import streamlit as st

from backend.vendor_database import init_db as init_vendor_db
from backend.user_database import init_user_db
from frontend.views.ai_settings_view import render_ai_settings_page
from frontend.views.login_view import render_login_page
from frontend.state_manager import init_session_state
from frontend.views.left_sidebar_view import render_left_sidebar
from frontend.views.main_col_view import render_main_col
from frontend.views.right_sidebar_view import render_right_sidebar
from frontend.views.shared_components_view import vertical_divider
from frontend.utils import run_analysis
from frontend.styles import get_styles
from frontend.views.vendors_page_view import render_vendors_page

def render_web_app() -> None:
    """Render the entire web app, including sidebars and main content."""

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

    # Native Left Sidebar (Navigation)
    with st.sidebar:
        render_left_sidebar()

    # Check if analysis is in progress - if so, show loading screen instead of normal UI
    if st.session_state.get("analysis_in_progress", False):

        st.markdown(get_styles("analysis_loading"), unsafe_allow_html=True)

        with st.spinner("🔄 Analyzing documents and generating report... This may take a minute."):
            run_analysis()
        
        st.stop()

    # Render settings page if selected
    if st.session_state.current_page == "Settings":
        render_ai_settings_page()
        
    # Render vendors page if selected
    elif st.session_state.current_page == "Vendors":
        render_vendors_page()

    # Otherwise, render dashboard by default
    else:

        # Main Area Split (Report & Documents)
        with st.container(key="app_shell"):
            mid_content, col_spacer, right_info = st.columns([0.79, 0.01, 0.20])

            with mid_content:
                render_main_col()

            # Vertical divider between the main content and right sidebar
            with col_spacer:
                vertical_divider("100vh")

            with right_info:
                render_right_sidebar()