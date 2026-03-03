import json
import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

from backend.models import Report, AIEvaluation
from backend.IO_engine import extract_text_from_pdf, extract_text_from_spreadsheet
from backend.config_manager import get_ai_instructions, get_ai_requirements, get_system_guidelines
from backend.vendor_database import (
    get_report_by_id,
    save_report,
    create_report_for_vendor,
    get_vendor_model_by_id,
    get_vendor_documents_path,
)
from backend.report_utils import calculate_score

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

def ai_evaluation(prompt: str, name: str | None, requirements: dict) -> AIEvaluation:
    """Run Gemini evaluation for a vendor prompt and normalize control metadata.

    Args:
        prompt (str): Full prompt containing instructions, requirements, and
            extracted document context.
        name (str | None): Vendor display name. Defaults to "Test Vendor"
            when "None".
        requirements (dict): Requirement configuration keyed by requirement name,
            containing metadata such as "weight" and "must_pass".

    Returns:
        AIEvaluation: Parsed AI response with controls adjusted to use
        configured "weight" and "must_pass" values.
    """

    if name is None:
        name = "Test Vendor"

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file in the project root.")

    # Setup AI API
    client = genai.Client(api_key=api_key)
    
    
    model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    response = client.models.generate_content(model=model_name,
                       contents=prompt,
                       config={
            "response_mime_type": "application/json",
            "response_schema": AIEvaluation}       # AIEvaluation defined in models.py
        )
    raw_results = response.parsed

    """


    # MOCK RESPONSE for testing
    ai_requirements = get_ai_requirements()
    raw_results = []
    for i, requirement in enumerate(ai_requirements):
        status = 0 if i % 4 == 0 else 1
        raw_results.append(SecurityControl(
            requirement=requirement,
            status=status,
            weight=-1,
            must_pass=False,
            evidence=f"Sample evidence for {requirement}"
        ))
        """

    corrected_controls = []

    # Map requirement details from config to ensure AI response is consistent with current settings
    for control in raw_results.controls:
        # Find the requirement config by matching the name field
        req_config = None
        for key, value in requirements.items():
            if value.get("name") == control.name:
                req_config = value
                break
        
        if req_config:
            control.requirement = req_config.get("description", "")
            control.weight = req_config.get("weight", 0)
            control.must_pass = req_config.get("must_pass", False)
        
        corrected_controls.append(control)

    # Create and return AIEvaluation object
    evaluation = AIEvaluation(
        vendor_name=raw_results.vendor_name,
        controls=corrected_controls,
        summary=raw_results.summary
    )
    return evaluation

def generate_prompt(report_row: dict) -> str:
    """Build the full AI prompt from report metadata and stored PDF files.

    Args:
        report_row (dict): Dictionary containing vendor metadata and file list.
            Must include 'vendor_id', 'vendor_name', and 'file_list_json'.

    Returns:
        str: Prompt text combining AI instructions, requirements, vendor name,
        and extracted text from all available documents.
    """

    vendor_id = report_row['vendor_id']
    vendor_name = report_row['vendor_name']
    
    # Use vendor documents folder instead of report storage path
    documents_path = get_vendor_documents_path(vendor_id)
    
    # Parse the file list from the DB
    file_names = json.loads(report_row['file_list_json'])

    # Construct the full paths to the relevant docs
    all_paths = [documents_path / name for name in file_names]

    # Read all relevant documents
    documents_context = ""
    for path in all_paths:
        if path.exists():
            # Determine file type and use appropriate extraction method
            file_ext = path.suffix.lower()
            
            if file_ext == '.pdf':
                file_text = extract_text_from_pdf(path)
            elif file_ext in ['.xlsx', '.xls', '.csv']:
                file_text = extract_text_from_spreadsheet(path)
            else:
                file_text = "Unsupported file type."
            
            documents_context += f"\nDocument Name: {path.name}\n"
            documents_context += f"Document Text:\n{file_text}\n"
            documents_context += "-" * 20 + "\n"

    # Load System Guidelines, Instructions and Requirements
    system_guidelines = get_system_guidelines()
    instructions = get_ai_instructions()
    requirements = get_ai_requirements()
    
    # Parse list of requirements into text using the name field
    req_list = [f"Requirement Name: {v['name']}\nRequirement Description: {v['description']}" for k, v in requirements.items()]

    vendor_row = get_vendor_model_by_id(vendor_id)
    bitsight_rating = "N/A"
    if vendor_row and vendor_row.bitsight_rating is not None:
        bitsight_rating = vendor_row.bitsight_rating

    # Combine system guidelines, instructions, requirements, and report into one prompt
    prompt = (
        f"{system_guidelines}\n\n"
        f"---\n\n"
        f"{instructions}\n\n"
        f"Requirements to check:\n" + "\n".join(req_list) + "\n\n"
        f"Name of Vendor: {vendor_name}\n\n"
        f"Bitsight Rating: {bitsight_rating}\n\n"
        f"--- START OF DOCUMENTS ---\n"
        f"{documents_context}"
        f"--- END OF DOCUMENTS ---"
    )

    return prompt

def generate_report(vendor_id: int) -> Report | None:
    """Create a new report for a vendor using all documents in their folder.

    Args:
        vendor_id (int): The vendor ID to create a report for.

    Returns:
        VendorReport | None: The new report with analysis results, or
        "None" if the vendor does not exist or has no documents.

    Workflow:
        1. Get all document files from the vendor's documents folder.
        2. Create a new report version for that vendor.
        3. Generate the AI prompt from all vendor documents.
        4. Request AI control evaluations.
        5. Save results to the new report version.
    """

    # 1. Get all document files from vendor's documents folder
    documents_path = get_vendor_documents_path(vendor_id)
    
    if not documents_path.exists():
        print(f"⚠️ No documents folder found for vendor {vendor_id}")
        return None
    
    # Get all PDF files in the vendor's documents folder
    file_names = sorted([f.name for f in documents_path.iterdir() if f.is_file() and f.suffix.lower() == '.pdf'])
    
    if not file_names:
        print(f"⚠️ No documents found for vendor {vendor_id}")
        return None

    # 2. Create a new report version for this vendor
    new_report_id = create_report_for_vendor(vendor_id)
    new_report_row = get_report_by_id(new_report_id)
    
    if not new_report_row:
        print(f"❌ Failed to create report for vendor {vendor_id}")
        return None
    
    # Build a dict for generate_prompt with vendor_id and files
    prompt_dict = {
        'vendor_id': vendor_id,
        'vendor_name': new_report_row['vendor_name'],
        'file_list_json': json.dumps(file_names)
    }

    # 3. Generate the AI prompt from all vendor documents
    prompt = generate_prompt(prompt_dict)
    
    # 4. Request AI control evaluations
    raw_results = ai_evaluation(prompt, new_report_row['vendor_name'], get_ai_requirements())

    # Create report
    report = Report(
        id=new_report_id,
        prompt=prompt,
        vendor_name=raw_results.vendor_name,
        overall_score=-1,   # Brief temporary value
        possible_score=-1,  # Brief temporary value
        summary=raw_results.summary,
        controls=raw_results.controls,
        file_names=file_names,
        storage_path=str(Path(new_report_row['storage_path'])),
        run_number=new_report_row['run_number'],
        timestamp=new_report_row['timestamp']
    )

    # 5. Recalculate score and save the updated report
    score, possible, ___ = calculate_score(report)

    report.overall_score = score
    report.possible_score = possible

    # Save in database
    save_report(report)

    return report