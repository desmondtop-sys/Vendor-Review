import streamlit as st

from defs import Page, Main_Col_Tabs

from backend.vendor_database import init_db as init_vendor_db
from backend.user_database import init_user_db
from backend.permissions import Permission
from backend.models import UserRole

from frontend.views.areas.left_sidebar_view import render_left_sidebar
from frontend.views.areas.main_col_view import render_main_col
from frontend.views.areas.right_sidebar_view import render_right_sidebar

from frontend.views.ai_settings_view import render_ai_settings_page
from frontend.views.client_side_views.client_upload_view import render_client_upload_page
from frontend.views.login_view import render_login_page
from frontend.views.shared_components_view import render_vertical_divider
from frontend.views.user_control_page_view import render_user_control_page
from frontend.views.vendors_page_view import render_vendors_page

from frontend.utils import run_analysis, get_pdf_passwords_from_ui
from frontend.styles import get_styles
from frontend.state_manager import init_session_state
from frontend.auth_helpers import current_user_has_permission, current_user_is

def render_web_app() -> None:
    """Render the entire web app, including sidebars and main content."""

    # Hide anchors over all elements
    st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # Page Config
    st.set_page_config(
        page_title="Hydro Ottawa Vendor Evaluator", 
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize databases
    init_vendor_db()
    init_user_db()
    
    init_session_state()

    # Check authentication - show login page if not logged in
    if not st.session_state.get("logged_in", False):
        render_login_page()
        return
    
    if current_user_is(UserRole.CLIENT):
        render_client_upload_page()
        return

    # Native Left Sidebar (Navigation)
    with st.sidebar:
        render_left_sidebar()

    # Check if analysis is in progress - if so, check for locked PDFs and prompt for passwords
    if st.session_state.get("analysis_in_progress", False):

        # Check if we've already prompted for passwords and are ready to generate
        if not st.session_state.get("ready_to_generate", False):
            # Show password prompt if there are locked PDFs
            get_pdf_passwords_from_ui()
        else:
            # Passwords have been provided, proceed with analysis
            st.markdown(get_styles("analysis_loading"), unsafe_allow_html=True)

            with st.spinner("🔄 Analyzing documents and generating report... This may take a minute."):
                run_analysis()
            
            st.stop()

    # Scoped-vendor users are restricted from admin surfaces (Vendors/Settings).
    # If they navigate there via stale state/URL, force-reset to Dashboard.
    if current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS) and st.session_state.current_page in {Page.VENDORS.value, Page.SETTINGS.value}:
        st.session_state.current_page = Page.DASHBOARD.value
        st.session_state.current_tab  = Main_Col_Tabs.DASHBOARD.value
        st.rerun()

    # Render settings page if selected
    if st.session_state.current_page == Page.SETTINGS.value:
        render_ai_settings_page()
        
    # Render vendors page if selected
    elif st.session_state.current_page == Page.VENDORS.value:
        render_vendors_page()

    elif st.session_state.current_page == Page.USER_CONTROL.value:
        render_user_control_page()

    # Otherwise, render dashboard by default
    else:

        # Main Area Split (Report & Documents)
        with st.container(key="app_shell"):
            mid_content, col_spacer, right_info = st.columns([0.77, 0.03, 0.20])

            with mid_content:
                render_main_col()

            # Vertical divider between the main content and right sidebar
            with col_spacer:
                render_vertical_divider("150vh")

            with right_info:
                render_right_sidebar()