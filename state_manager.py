import streamlit as st
import copy

from backend.models import Report
from backend.vendor_database import (
    get_latest_report_for_vendor,
    get_active_report_for_vendor,
    get_report_by_id,
    set_active_report_for_vendor,
    generate_vendor_report_from_db
)

def mark_dirty() -> None:
    """Mark AI settings as modified in Streamlit session state."""

    st.session_state.is_dirty = True

def reset_states() -> None:
    """Reset transient UI widget state used across screens.

    Increments uploader key version so Streamlit renders a fresh file uploader
    instance and clears the prior upload widget state.
    """
    st.session_state.uploader_id += 1

def init_session_state() -> None:
    """Initialize default Streamlit session-state keys.

    Sets uploader and navigation defaults the first time a user session loads.
    """
    # Authentication state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_full_name" not in st.session_state:
        st.session_state.user_full_name = None
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    
    # Application state
    if "uploader_id" not in st.session_state: 
        st.session_state.uploader_id = 0
    if "current_page" not in st.session_state: 
        st.session_state.current_page = "Dashboard"
    if "current_tab" not in st.session_state: 
        st.session_state.current_tab = "Dashboard"
    if "active_vendor_id" not in st.session_state:
        st.session_state.active_vendor_id = None
    if "active_report" not in st.session_state:
        st.session_state.active_report = None

def handle_vendor_switch(vendor_id: int) -> None:
    """Switch active vendor and load its saved active report, or latest if none saved.

    Args:
        vendor_id (int): Vendor identifier to switch to.
    """
    st.session_state.active_vendor_id = vendor_id
    
    # Try to load the saved active report for this vendor
    saved_report_id = get_active_report_for_vendor(vendor_id)
    
    if saved_report_id:
        # Load the saved report
        saved_report_row = get_report_by_id(saved_report_id)
        if saved_report_row:
            st.session_state.active_report = generate_vendor_report_from_db(saved_report_row)
        else:
            # Saved report doesn't exist anymore, load latest instead
            latest_report_row = get_latest_report_for_vendor(vendor_id)
            if latest_report_row:
                st.session_state.active_report = generate_vendor_report_from_db(latest_report_row)
            else:
                st.session_state.active_report = None
    else:
        # No saved report, load the latest one
        latest_report_row = get_latest_report_for_vendor(vendor_id)
        if latest_report_row:
            st.session_state.active_report = generate_vendor_report_from_db(latest_report_row)
        else:
            st.session_state.active_report = None
    
    reset_states()  # Clear uploader
    reset_sandbox()  # Kill old simulation

    # Go back to dashboard
    st.session_state.current_page = "Dashboard"
    st.session_state.current_tab = "Dashboard"

    st.rerun()


def handle_report_switch(new_report: Report) -> None:
    """Switch active report, save it to the vendor, and reset UI state to dashboard defaults.

    Args:
        new_report (VendorReport): Report object to set as the active report.
    """
    st.session_state.active_report = new_report
    if "live_pdf_data" in st.session_state:
        st.session_state.live_pdf_data = None
    
    # Save this report as the active report for the current vendor
    if st.session_state.active_vendor_id and new_report.id:
        set_active_report_for_vendor(st.session_state.active_vendor_id, new_report.id)
    
    reset_states() # Clear uploader
    reset_sandbox() # Kill old simulation

    # Go back to dashboard
    st.session_state.current_page = "Dashboard"
    st.session_state.current_tab = "Dashboard"

    st.rerun()


def reset_sandbox() -> None:
    """Clear simulation state and bump widget version for UI refresh.

    Removes simulation data from session state and increments the simulation
    version so Streamlit widgets rebind to fresh keys.
    """
    if "simulation_report" in st.session_state:
        del st.session_state.simulation_report

    # Make a new sim version to force the UI to update properly
    if "sim_version" not in st.session_state:
        st.session_state.sim_version = 0
    st.session_state.sim_version += 1

def initialize_simulation() -> None:
    """Initialize simulation state from the active report when needed.
    
    Creates a deep copy so changes to simulation don't affect the original report.
    """

    if "active_report" in st.session_state and "simulation_report" not in st.session_state:

        # We use deepcopy so changes to sim_report don't affect the original object
        st.session_state.simulation_report = copy.deepcopy(st.session_state.active_report)
        
        # Initialize a fresh version for widget keys
        if "sim_version" not in st.session_state:
            st.session_state.sim_version = 0

def sync_sim_control(req_name: str, slider_key: str) -> None:
    """Sync a weight slider value to the matching control in simulation data.

    Args:
        req_name: Requirement name identifying the control to update.
        slider_key: Session-state key containing the latest slider value.
    """
    sim_report = st.session_state.simulation_report
    for control in sim_report.controls:
        if control.requirement == req_name:
            # Update Weight from Slider
            control.weight = st.session_state[slider_key]

def sync_sim_status(req_name: str, select_key: str) -> None:
    """Sync pass/fail selectbox choice to a control's binary status value.

    Args:
        req_name: Requirement name identifying the control to update.
        select_key: Session-state key containing the selected label.
    """
    sim_report = st.session_state.simulation_report
    choice = st.session_state[select_key]
    
    for ctrl in sim_report.controls:
        if ctrl.requirement == req_name:
            ctrl.status = 1 if "Pass" in choice else 0 # Simple binary toggle
            break