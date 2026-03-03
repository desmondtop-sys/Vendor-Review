
from backend.vendor_database import get_report_by_id, generate_vendor_report_from_db
from backend.models import SecurityControl, Report

def calculate_score(report: Report) -> tuple[int | float, int | float, bool]:
    """Compute achieved score, possible score, and must-pass failure flag.

    Args:
        report (VendorReport): Report containing controls and excluded
            names.

    Returns:
        tuple[int | float, int | float, bool]:
            "(score, possible, must_pass_failed)" for included controls.
    """

    # Default values
    score = 0
    possible = 0
    must_pass_failed = False

    # Evaluate controls. Return default values if none exist
    if report and report.controls:
        for control in report.controls:
            
            if control.name not in report.excluded_names:
                score += (control.status * control.weight)
                possible += control.weight

                if control.must_pass and control.status == 0:
                    must_pass_failed = True

    return score, possible, must_pass_failed

def calculate_total_weight(session_state) -> int | float:
    """Sum requirement weights from Streamlit session state.

    Args:
        session_state: Streamlit session state containing weight values for requirements.

    Returns:
        int | float: Total weight across all requirements.
    """
    total_weight = 0

    # Access the requirements stored in temp_requirements to keep an active total 
    # even when weights haven't been saved to the config file yet
    for key in session_state.temp_requirements.keys():

        # Streamlit keys for weight are f"weight_{key}"
        weight_key = f"weight_{key}"

        if weight_key in session_state:
            total_weight += session_state[weight_key]

        else:
            # Fallback for the very first load
            total_weight += session_state.temp_requirements[key].get("weight", 0)

    return total_weight

def get_security_score_by_id(report_id: int) -> tuple[int | float, int | float, bool]:
    """Load a report by ID and return its computed security score tuple.

    Args:
        report_id (int): Report identifier.

    Returns:
        tuple[int | float, int | float, bool]: Score tuple from
        "calculate_score". Returns "(0, 100, False)" when report is missing.
    """
    db_data = get_report_by_id(report_id)
    if not db_data:
        return 0, 100, False
        
    report = generate_vendor_report_from_db(db_data)
    return calculate_score(report)

def get_control_by_name(report: Report, name: str) -> SecurityControl | None:
    """Find the first control in a report that matches a requirement name.

    Args:
        report (VendorReport): Report containing control entries.
        name (str): Requirement name to match.

    Returns:
        SecurityControl | None: Matching control, or "None" if not found.
    """
    match = [c for c in report.controls if c.requirement == name]
    
    return match[0] if match else None


def report_to_string(report: Report) -> str:
    """Create a concise printable summary string for a report object.

    Args:
        report (VendorReport): Report to summarize.

    Returns:
        str: Pipe-separated summary containing ID, vendor name, file list, and
        storage path.
    """
    output = [
        f"\nID: {report.id}",
        f"\nVendor Name: {report.vendor_name}",
        f"\nFile List: {', '.join(report.file_names) if report.file_names else '[]'}",
        f"\nStorage Path: {report.storage_path}"
    ]
    
    return " | ".join(output)