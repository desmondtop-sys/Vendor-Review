import sqlite3
import streamlit as st

from backend.config_manager import get_ai_requirements, get_threshold_settings
from backend.report_utils import calculate_score, calculate_total_weight, report_to_string
from backend.vendor_database import create_report_for_vendor, generate_vendor_report_from_db, get_report_by_id, save_report, update_vendor, get_latest_report_for_vendor, set_active_report_for_vendor
from backend.models import Report
from backend.AI_logic import generate_report

from frontend.state_manager import handle_report_switch, reset_states, reset_sandbox

def run_analysis() -> None:
    """Execute the AI analysis of uploaded documents with full-screen spinner overlay."""
    
    vendor_id = st.session_state.get("active_vendor_id")
    
    try:
        # Generate Report and create a new report version
        new_report = generate_report(vendor_id)
        
        if new_report:
            # Update vendor name with the AI-provided name
            update_vendor_name(new_report.vendor_name)
            
            # Load the latest report (which should be the new version)
            latest_report_row = get_latest_report_for_vendor(vendor_id)
            st.session_state.active_report = generate_vendor_report_from_db(latest_report_row)
            # Save this as the active report for the vendor
            if latest_report_row:
                set_active_report_for_vendor(vendor_id, latest_report_row['id'])
            st.success("Analysis Complete!")
        else:
            st.error("Analysis Failed.")
    finally:
        st.session_state.analysis_in_progress = False
        reset_states()
        reset_sandbox()
        st.session_state.current_tab = "Dashboard"
        st.rerun()

def save_simulation_as_new_report() -> None:
    """Create a new report version from the current simulation state."""

    vendor_id = st.session_state.get("active_vendor_id")
    sim_report = st.session_state.get("simulation_report")

    if not vendor_id or not sim_report:
        st.warning("No simulation data available to save.")
        return

    new_report_id = create_report_for_vendor(vendor_id)
    if not new_report_id:
        st.error("Failed to create a new report entry.")
        return

    db_row = get_report_by_id(new_report_id)
    if not db_row:
        st.error("Failed to load the new report entry.")
        return

    new_report = generate_vendor_report_from_db(db_row)
    score, possible, _ = calculate_score(sim_report)

    new_report.prompt = sim_report.prompt
    new_report.vendor_name = sim_report.vendor_name
    new_report.controls = sim_report.controls
    new_report.summary = sim_report.summary
    new_report.overall_score = int(score)
    new_report.possible_score = int(possible)
    new_report.file_names = list(sim_report.file_names)
    new_report.excluded_names = list(sim_report.excluded_names)

    # Check if report still exists before saving
    if not get_report_by_id(new_report.id):
        st.error("Report was deleted. Could not save simulation.")
        return

    try:
        save_report(new_report)
        st.toast("Simulation saved as a new report version.")
        handle_report_switch(new_report)
    except RuntimeError as e:
        st.error(f"Could not save simulation: {str(e)}")

def update_vendor_name(new_name: str) -> None:
    """Persist vendor name edits into the vendors table and active report.

    Args:
        new_name (str): Vendor name to persist.
    """
    vendor_id = st.session_state.get("active_vendor_id")
    
    if not vendor_id:
        return

    # Save as default in case we need to auto-suffix due to a name conflict
    final_name = new_name

    # Update vendor name in vendors table
    try:
        update_vendor(vendor_id, new_name)

    # If the vendor name already exists, auto-suffix with a number until it succeeds
    except sqlite3.IntegrityError:
        counter = 2
        while True:
            candidate = f"{new_name} {counter}"
            try:
                update_vendor(vendor_id, candidate)
                final_name = candidate
                break
            except sqlite3.IntegrityError:
                counter += 1

            # Fail-safe to prevent infinite loop in case of unexpected issues
            if counter > 100:
                return
    
    # Also update the active report if one exists
    report = st.session_state.get("active_report")
    if report:
        report.vendor_name = final_name
        # Check if report still exists before saving
        if not get_report_by_id(report.id):
            st.warning("Could not update report vendor name: Report was deleted.")
            return
        try:
            save_report(report)
        except RuntimeError as e:
            st.warning(f"Could not update report vendor name: {str(e)}")

    st.session_state["vendor_name_text_area"] = final_name

def get_current_view_report() -> Report | None:
    """Return the report object currently shown in the UI.

    Returns the simulation report while on the Analysis Tools tab when present;
    otherwise returns the active report from session state.

    Returns:
        VendorReport | None: Simulation or active report, if available.
    """

    if st.session_state.get("current_tab") == "Analysis Tools" and "simulation_report" in st.session_state:
        return st.session_state.simulation_report
    
    return st.session_state.get("active_report")
    
def get_badge_values() -> tuple:
    """Calculate and return badge values for total weight display.
    
    Returns:
        tuple: (badge_bg_color, badge_text_color, badge_label)
    """
    # Calculate the total weight for real-time validation
    try:
        # We initialize a temporary dictionary so we can show calculations before the user actually clicks Save
        if "temp_requirements" not in st.session_state or st.session_state.temp_requirements is None:
            # Use cached requirements from session (loaded at login)
            st.session_state.temp_requirements = st.session_state.get("cached_ai_requirements", get_ai_requirements())

        total_weight = calculate_total_weight(st.session_state)
        
        badge_bg, badge_text = "#d4edda", "#155724"
        badge_label = f"{total_weight}"
    except Exception as e:
        badge_bg, badge_text = "#f8d7da", "#721c24"
        badge_label = "🚫 JSON Error"
    
    return badge_bg, badge_text, badge_label

def get_badge_styles(score, possible, must_pass_failed) -> tuple[str, str, str]:
    """Determine badge styles based on score and thresholds."""

    if possible <= 0:
        status = "❌ FAILED"
        color = "#f8d7da"
        text_color = "#721c24"
        return status, color, text_color
    
    score_pct = (score / possible) * 100

    # Use cached thresholds from session (loaded at login)
    thresholds = st.session_state.get("cached_threshold_settings", get_threshold_settings())
    pass_limit = thresholds["pass_threshold"]
    fail_limit = thresholds["fail_threshold"]

    if must_pass_failed:
        status = "🛑 CRITICAL FAILURE"
        color = "#f8d7da"
        text_color = "#721c24"
    elif score_pct >= pass_limit:
        status = "✅ PASSED"
        color = "#d4edda"
        text_color = "#155724"
    elif score_pct >= fail_limit:
        status = "⚠️ NEEDS REVIEW"
        color = "#fff3cd"
        text_color = "#856404"
    else:
        status = "❌ FAILED"
        color = "#f8d7da"
        text_color = "#721c24"
    
    return status, color, text_color

def active_report_to_string() -> str:
    """Return a printable summary string for the active report.

    Returns:
        str: Active report summary, or a fallback message when missing.
    """

    if "active_report" not in st.session_state:
        return "No active report found in session state."
    
    report = st.session_state.active_report
    
    return report_to_string(report)
