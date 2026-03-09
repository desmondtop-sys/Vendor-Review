import streamlit as st

from backend.vendor_database import (
    generate_vendor_report_from_db,
    get_all_vendor_models,
    get_latest_report_for_vendor,
    get_vendor_model_by_id,
)
from backend.permissions import Permission

from frontend.views.report_views.analysis_tab_view import render_analysis_tools
from frontend.views.report_views.assets_tab_view import render_assets_page
from frontend.views.report_views.compare_tab_view import render_compare_reports
from frontend.views.report_views.dashboard_tab_view import render_dashboard
from frontend.views.report_views.report_history_tab_view import render_report_history
from frontend.views.shared_components_view import render_security_score

from frontend.styles import get_styles
from frontend.utils import get_current_view_report, update_vendor_name
from frontend.state_manager import handle_vendor_switch
from frontend.auth_helpers import current_user_has_permission

def validate_active_vendor() -> None:
    """Validate that the active vendor still exists in the database.
    
    If the vendor has been deleted, clear the active_vendor_id and select 
    another vendor or show a message to the user.
    """
    vendor_id = st.session_state.get("active_vendor_id")
    assigned_vendor_id = st.session_state.get("user_assigned_vendor_id")

    # Scoped-vendor users are restricted to a single assigned vendor.
    if current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        if assigned_vendor_id is None:
            st.session_state.active_vendor_id = None
            st.session_state.active_report = None
            return

        if vendor_id != assigned_vendor_id:
            st.session_state.active_vendor_id = assigned_vendor_id
            st.session_state.active_report = None
            st.rerun()
    
    if vendor_id is None:
        return  # No vendor selected, nothing to validate
    
    # Check if the vendor still exists
    vendor = get_vendor_model_by_id(vendor_id)
    
    if vendor is None:
        # Vendor was deleted, clear the active vendor
        st.session_state.active_vendor_id = None
        st.session_state.active_report = None
        st.warning("🗑️ The vendor you were viewing has been deleted. Please select another vendor.")
        st.rerun()

def render_main_col() -> None:
    """Render the main app column and route between dashboard and analysis views."""

    # Title
    with st.container(key="main_title"):
        st.title("⚡ Vendor Security Evaluator")

    # Validate that the active vendor still exists (handles deletion by other users)
    validate_active_vendor()

    # If there's no vendor selected, select the first one available
    if "active_vendor_id" not in st.session_state or st.session_state.active_vendor_id is None:

        vendors = get_all_vendor_models()

        if current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
            assigned_vendor_id = st.session_state.get("user_assigned_vendor_id")
            vendors = [vendor for vendor in vendors if vendor.id == assigned_vendor_id]

        if vendors:
            # Select the first vendor
            handle_vendor_switch(vendors[0].id)
            st.rerun()

    # Default View, if still no vendor is loaded
    if st.session_state.get("active_vendor_id") is None:
        render_default_view()
        return
    
    # If there's no report selected, select the first one available for the vendor
    if "active_report" not in st.session_state or st.session_state.active_report is None:

        # Select the latest report for the active vendor
        vendor_id = st.session_state.active_vendor_id
        latest_report_row = get_latest_report_for_vendor(vendor_id)
        if latest_report_row:
            st.session_state.active_report = generate_vendor_report_from_db(latest_report_row)
            st.rerun()

    render_vendor_title()
    
    render_dashboard_tabs()

    # Route to the correct tab view
    if st.session_state.current_tab == "Dashboard":
        render_dashboard()
        
    elif st.session_state.current_tab == "Analysis Tools":
        render_analysis_tools()

    elif st.session_state.current_tab == "Assets":
        render_assets_page()

    elif st.session_state.current_tab == "Report History":
        render_report_history()

    elif st.session_state.current_tab == "Compare Reports":
        render_compare_reports()

def render_default_view() -> None:
    """Render onboarding instructions shown when no vendors exist."""

    st.markdown("""
        ### Welcome to the Vendor Evaluator
        To begin a new security assessment, please follow these steps:
        
        1. **Create a Vendor**: Use the "New Vendor" button on the left sidebar to add a vendor.
        2. **Upload Evidence**: Use the panel on the right to upload SOC 2 reports, Penetration Tests, or other security documentation.
        3. **Generate Report**: Click 'Generate Report' to trigger the AI-powered requirement check.
        4. **Review Results**: The report will populate here once the analysis is complete.
        
        *Alternatively, select an existing vendor from the **Vendors** list on the left.*
    """, unsafe_allow_html=True)



def render_vendor_title() -> None:
    """Render the vendor name as an editable text area and the security score card."""

    st.markdown(get_styles("vendor_title"), unsafe_allow_html=True)

    st.divider()

    vendor_id = st.session_state.get("active_vendor_id")
    if not vendor_id:
        return

    if current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        assigned_vendor_id = st.session_state.get("user_assigned_vendor_id")
        if vendor_id != assigned_vendor_id:
            st.warning("⚠️ Access denied for this vendor.")
            return

    vendor = get_vendor_model_by_id(vendor_id)
    if not vendor:
        return

        
    col_name, col_score = st.columns([0.65, 0.35])
    with col_name:
        
        label_col, input_col = st.columns([0.25, 0.75])

        with label_col:
            # Use a div to apply Vendor style
            st.markdown('<p class="vendor-title">Vendor:</p>', unsafe_allow_html=True)

        # Set up the text area
        with input_col:
            
            # Ensure vendor name is populated before rendering
            current_text = st.session_state.get("vendor_name_text_area", "").strip()
            if not current_text:
                st.session_state["vendor_name_text_area"] = vendor.name or "New Vendor"
            
            # Wrap text area with style
            with st.container(key="vendor_header_area"):
                st.text_area(
                    "Vendor Name",
                    key="vendor_name_text_area",
                    on_change=lambda: update_vendor_name(
                        st.session_state.vendor_name_text_area
                    ),
                    label_visibility="collapsed"
                )

    with col_score:
        with st.container(key="main_vendor_score"):
            render_security_score(get_current_view_report())

def render_dashboard_tabs() -> None:
    """Render tab buttons for switching between dashboard, analysis tools, and report history."""

    # Initialize tab variable
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "Dashboard"

    tab1, tab2, tab3, tab4, tab5 = st.columns([0.2, 0.2, 0.2, 0.2, 0.2])

    with tab1:
        type1 = "primary" if st.session_state.current_tab == "Dashboard" else "secondary"

        if st.button("Dashboard", type=type1, width='stretch'):
            st.session_state.current_tab = "Dashboard"
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_tab == "Analysis Tools" else "secondary"
        
        if st.button("Analysis Tools", type=type2, width='stretch'):
            st.session_state.current_tab = "Analysis Tools"
            st.rerun()

    with tab3:
        type3 = "primary" if st.session_state.current_tab == "Assets" else "secondary"
        
        if st.button("Assets", type=type3, width='stretch'):
            st.session_state.current_tab = "Assets"
            st.rerun()

    with tab4:
        type4 = "primary" if st.session_state.current_tab == "Report History" else "secondary"
        
        if st.button("Report History", type=type4, width='stretch'):
            st.session_state.current_tab = "Report History"
            st.rerun()

    with tab5:
        type5 = "primary" if st.session_state.current_tab == "Compare Reports" else "secondary"
        
        if st.button("Compare Reports", type=type5, width='stretch'):
            st.session_state.current_tab = "Compare Reports"
            st.rerun()

    st.divider()

