"""PDF report generation for vendor security assessments.

Generates professional PDF documents containing security scores,
requirement breakdowns, visualizations, and evidence summaries.
"""

import io
import os
from pathlib import Path
from fpdf import FPDF
import pandas as pd
from pypdf import PdfReader
import streamlit as st

from backend.config_manager import get_threshold_settings
from backend.report_utils import check_critical_failure, get_security_score_by_id
from backend.charts import generate_report_pie_chart

import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)

# Get paths
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
LOGO_PATH = ROOT_DIR / "Resources" / "hydro_ottawa_logo.png"


class PDF(FPDF):
    """Custom PDF class with Hydro Ottawa logo header on each page."""
    
    def header(self):
        """Add logo to top left corner of each page."""
        if LOGO_PATH.exists():
            # Add logo - position it in top left corner
            # x=10, y=8, width=30mm
            self.image(str(LOGO_PATH), x=10, y=8, w=30)
        # Add some space after the header
        self.ln(28)

def detect_locked_pdfs(directory_path: str | os.PathLike) -> list[str]:
    """Detect PDFs that actually require a password to read content.
    
    This function tests whether PDFs can be read without a password.
    Some PDFs have encryption flags but can still be opened without one.

    Args:
        directory_path (str | os.PathLike): Path to directory containing PDFs.

    Returns:
        list[str]: List of PDF filenames that actually require a password to extract text.
    """
    locked_files = []
    dir_path = Path(directory_path)
    
    if not dir_path.exists():
        return locked_files
    
    for file_path in dir_path.iterdir():
        if file_path.suffix.lower() == '.pdf' and file_path.is_file():
            try:
                reader = PdfReader(file_path)
                
                # Try to read at least one page to verify we can access content
                if len(reader.pages) > 0:
                    # Attempt to extract text from the first page
                    _ = reader.pages[0].extract_text()
                    # If we got here, the PDF is readable
                    continue
                else:
                    # Empty PDF, not locked
                    continue
                    
            except Exception as e:
                # If extraction fails, check if it's due to encryption
                error_msg = str(e).lower()
                if "encrypt" in error_msg or "password" in error_msg or "decrypt" in error_msg:
                    locked_files.append(file_path.name)
                # Otherwise, it might be corrupted but not password-protected
    
    return locked_files

def extract_text_from_pdf(pdf_path: str | os.PathLike, password: str | None = None) -> str:
    """Extract and concatenate text from all pages in a PDF file.
    
    Also extracts form field values for filled forms.

    Args:
        pdf_path (str | os.PathLike): Path to the PDF document on disk.
        password (str | None): Optional password for encrypted PDFs.

    Returns:
        str: Combined text content from every page plus form field values.
        Returns error message if file is locked, corrupted, or cannot be read.
        Returns "Not Found." when the file does not exist.
    """
    
    # Check if the file actually exists before trying to open it
    if not os.path.exists(pdf_path):
        return "Not Found."
    
    try:
        # If it exists, read it normally
        reader = PdfReader(pdf_path)
        
        # Check if the PDF is encrypted
        if reader.is_encrypted:
            if password:
                # Try to decrypt with provided password
                if not reader.decrypt(password):
                    return f"Error: Incorrect password for encrypted PDF."
            else:
                return f"Error: PDF is password-protected. Please provide the password to unlock it."
        
        text = ""
        
        # Extract form field values first (for filled questionnaires, etc.)
        fields = reader.get_fields()
        if fields:
            for field_name, field in fields.items():
                # Get the field value
                field_value = field.get("/V")
                if field_value:
                    text += f"{field_name}: {field_value}\n"
        
        # Then extract regular page text
        for page in reader.pages:
            text += page.extract_text()
        
        return text
    
    except Exception as e:
        return f"Error reading PDF (possibly locked or corrupted): {str(e)}"

def extract_text_from_spreadsheet(file_path: str | os.PathLike) -> str:
    """Extract and format data from spreadsheet files (Excel, CSV).

    Args:
        file_path (str | os.PathLike): Path to the spreadsheet file on disk.

    Returns:
        str: Formatted text representation of the spreadsheet content.
        Returns "Not Found." when the file does not exist.
    """
    
    # Check if the file actually exists before trying to open it
    if not os.path.exists(file_path):
        return "Not Found."
    
    file_ext = Path(file_path).suffix.lower()
    text = ""
    
    try:
        # Read based on file extension
        if file_ext in ['.xlsx', '.xls']:
            # Read all sheets from Excel file
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                text += f"\n=== Sheet: {sheet_name} ===\n"
                text += df.to_string(index=False)
                text += "\n\n"
        elif file_ext == '.csv':
            # Read CSV file
            df = pd.read_csv(file_path)
            text += df.to_string(index=False)
        else:
            return "Unsupported file format."
        
        return text.strip()
    
    except Exception as e:
        return f"Error reading spreadsheet: {str(e)}"

def generate_pdf_report() -> bytes:
    """Build a PDF summary for the active report in Streamlit session state.

    Returns:
        bytes: Binary PDF payload ready for download or file writing.

    Workflow:
        1. Read active report and compute score totals.
        2. Resolve pass/fail status using configured thresholds.
        3. Render summary text, score box, and pie chart.
        4. Append per-control evidence breakdown.

    Notes:
        - Excluded requirements are omitted from detailed breakdown.
        - Status becomes "CRITICAL FAILURE" if any must-pass control fails, or if any control marked critical for sensitive data fails when data type is Confidential/Restricted.
    """
    report = st.session_state.active_report

    if not report:
        return b""

    score, possible, critical_failure = get_security_score_by_id(report.id)
    thresholds = get_threshold_settings()
    
    # Calculate Result
    percentage = (score / possible) * 100 if possible > 0 else 0
    if critical_failure:
        result_text = "CRITICAL FAILURE"
    elif percentage >= thresholds["pass_threshold"]:
        result_text = "PASSED"
    elif percentage >= thresholds["fail_threshold"]:
        result_text = "NEEDS REVIEW"
    else:
        result_text = "FAILED"

    pdf = PDF()
    pdf.add_page()
    
    # Header & Summary
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 10, "Vendor Security Audit Report", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    clean_vendor_name = report.vendor_name.encode('ascii', 'ignore').decode('ascii')
    pdf.cell(0, 10, f"Vendor: {clean_vendor_name}", ln=True, align="C")
    
    # Add data type
    data_type_str = report.data_type.value if report.data_type else "Not Specified"
    pdf.set_font("Arial", "I", 11)
    pdf.cell(0, 8, f"Data Type: {data_type_str}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)

    # Visual status card uses green for pass and red for all non-pass outcomes.
    if result_text == "PASSED":
        result_color = (40, 120, 60)
    else:
        result_color = (150, 50, 50)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(*result_color)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 15, f"Security Score: {score} / {possible} ({percentage:.2f}%)", border=1, ln=True, align="C", fill=True)
    pdf.cell(0, 10, f"Status: {result_text}", border=1, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # AI Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "AI Summary", ln=True)
    pdf.set_font("Arial", "", 10)
    clean_summary = (report.summary or "No summary provided.").encode('ascii', 'ignore').decode('ascii')
    pdf.multi_cell(0, 6, clean_summary)
    pdf.ln(6)

    fig = generate_report_pie_chart(report)
    fig.update_layout(
        showlegend=True,
        margin=dict(l=0, r=0, t=30, b=20)
    )
    img_bytes = fig.to_image(format="png", width=600, height=350, scale=2)
    img_buffer = io.BytesIO(img_bytes)

    # Insert image into PDF
    pdf.image(img_buffer, x="C", y=None, w=190)
    pdf.ln(5)

    # Requirement Breakdown
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Detailed Requirement Breakdown", ln=True)
    pdf.set_font("Arial", "", 10)

    # Only include controls that were not excluded by the user in the report view. This ensures the PDF reflects exactly what the user sees in their report, including any manual exclusions.
    controls = [c for c in report.controls if c.name not in report.excluded_names]
    
    for control in controls:
            
        pdf.set_font("Arial", "B", 10)

        if check_critical_failure(control, report.data_type):
            status = "CRITICAL FAIL"
            pdf.set_text_color(150, 50, 50)
        elif control.status == 1:
            status = "PASS"
            pdf.set_text_color(40, 120, 60)
        else:
            status = "FAIL"
            pdf.set_text_color(150, 50, 50)

        # Clean the control requirement text for PDF compatibility
        clean_requirement = control.name.encode('ascii', 'ignore').decode('ascii')
        pdf.cell(0, 8, f"[{status}] {clean_requirement} ({control.weight} pts)", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        # Clean the evidence text for PDF compatibility
        clean_evidence = control.evidence.encode('ascii', 'ignore').decode('ascii')
        pdf.multi_cell(0, 6, f"Evidence: {clean_evidence}")
        pdf.ln(4)


    # Full audit prompt
    pdf.add_page() # Start prompt on a new page for clarity
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Technical Prompt", ln=True)
    pdf.cell(0, 6, "Full prompt sent to the AI model:", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Courier", "", 8) # Use monospace to denote raw data
    pdf.set_text_color(20, 20, 20) # Grey for the technical log
    
    # Truncate prompt before documents section for readability
    prompt_text = report.prompt if report.prompt else "No prompt data."
    if "--- START OF DOCUMENTS ---" in prompt_text:
        prompt_text = prompt_text.split("--- START OF DOCUMENTS ---")[0].strip()

    clean_prompt = prompt_text.encode('ascii', 'ignore').decode('ascii')

    pdf.multi_cell(0, 5, clean_prompt)

    # Add section listing all files included in the analysis
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)  # Reset to black
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Documents Analyzed", ln=True)
    pdf.set_font("Arial", "", 10)
    
    if report.file_names:
        for file_name in report.file_names:
            clean_file_name = file_name.encode('ascii', 'ignore').decode('ascii')
            pdf.cell(0, 8, f"  - {clean_file_name}", ln=True)
    else:
        pdf.cell(0, 8, "  No documents included", ln=True)

    return bytes(pdf.output())