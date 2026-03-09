import sqlite3
import streamlit as st

from backend.config_manager import get_ai_requirements, get_threshold_settings
from backend.report_utils import calculate_score, calculate_total_weight, report_to_string
from backend.vendor_database import create_report_for_vendor, generate_vendor_report_from_db, get_report_by_id, save_report, update_vendor, get_latest_report_for_vendor, set_active_report_for_vendor, get_vendor_documents_path
from backend.models import Report
from backend.AI_logic import generate_report
from backend.IO_engine import detect_locked_pdfs
from backend.pdf_password_manager import load_pdf_passwords, save_pdf_passwords

from frontend.state_manager import handle_report_switch, reset_states, reset_sandbox

def get_pdf_passwords_from_ui() -> dict:
    """Display a form to collect passwords for locked PDFs in the active vendor's folder.
    
    Loads previously saved passwords and allows user to update or override them.
    
    Returns:
        dict: Dictionary mapping PDF filenames to their passwords.
    """
    vendor_id = st.session_state.get("active_vendor_id")
    if not vendor_id:
        return {}
    
    documents_path = get_vendor_documents_path(vendor_id)
    locked_files = detect_locked_pdfs(documents_path)
    
    if not locked_files:
        # No locked files, proceed directly to analysis
        st.session_state.ready_to_generate = True
        st.session_state.pdf_passwords = {}
        st.rerun()
        return {}
    
    # Load previously saved passwords
    saved_passwords = load_pdf_passwords(vendor_id)
    saved_files = [f for f in locked_files if f in saved_passwords]
    unsaved_files = [f for f in locked_files if f not in saved_passwords]
    
    # If all locked files have saved passwords, proceed directly to analysis
    if not unsaved_files:
        st.session_state.pdf_passwords = saved_passwords
        st.session_state.ready_to_generate = True
        st.rerun()
        return saved_passwords
    
    # Show warning and password form
    st.warning(f"⚠️ {len(locked_files)} PDF(s) are password-protected")
    
    if saved_files:
        st.success(f"✅ Found saved passwords for {len(saved_files)} file(s)")
        with st.expander("View saved files"):
            for filename in saved_files:
                st.write(f"  • {filename}")
    
    if unsaved_files:
        st.info(f"🔐 {len(unsaved_files)} file(s) need password(s)")
    
    st.info("💡 Tip: Leave passwords blank for files you don't have the password for. They will be skipped during analysis.")
    
    passwords = {}
    
    # Create a form for each locked file
    with st.form("pdf_passwords_form"):
        st.write("**Enter passwords (optional - leave blank to skip files):**")

        # Show unsaved files
        if unsaved_files:
            st.write("_New passwords:_")
            for filename in unsaved_files:
                password = st.text_input(
                    f"Password for {filename}",
                    type="password",
                    help="Enter the password to unlock this PDF. Leave blank to skip this file.",
                    key=f"pwd_{filename}"
                )
                if password:
                    passwords[filename] = password
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("🚀 Analyze Report", type="primary", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submit:
            # Save passwords and proceed with analysis
            save_pdf_passwords(vendor_id, passwords)
            st.session_state.pdf_passwords = passwords
            st.session_state.ready_to_generate = True
            st.rerun()
        
        if cancel:
            st.session_state.analysis_in_progress = False
            st.rerun()
    
    return passwords

def run_analysis() -> None:
    """Execute the AI analysis of uploaded documents with full-screen spinner overlay."""
    
    vendor_id = st.session_state.get("active_vendor_id")
    pdf_passwords = st.session_state.get("pdf_passwords", {})
    
    try:
        # Generate Report and create a new report version
        new_report = generate_report(vendor_id, pdf_passwords=pdf_passwords)
        
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
            st.error("Analysis Failed: generate_report() returned None. Check logs.")
    except Exception as e:
        st.error(f"Analysis Failed with error: {str(e)}")
        print(f"❌ Analysis error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        st.session_state.analysis_in_progress = False
        st.session_state.pdf_passwords = {}  # Clear passwords after use
        st.session_state.pending_passwords_to_save = {}
        st.session_state.ready_to_generate = False
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

    # Keep the original candidate; may be replaced if uniqueness conflict occurs.
    final_name = new_name

    # Update vendor name in vendors table
    try:
        update_vendor(vendor_id, new_name)

    # If the vendor name already exists, auto-suffix with a number until it succeeds
    except sqlite3.IntegrityError:

        # If the base name conflicts, append an incrementing suffix ("Name 2", "Name 3", ...)
        # until we find a unique value or hit a safe upper bound.
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
                st.error("Could not generate a unique vendor name. Please choose a different name.")
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
