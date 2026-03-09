import streamlit as st

from backend.vendor_database import create_vendor
from backend.permissions import Permission

from frontend.auth_helpers import current_user_has_permission
from frontend.styles import get_styles
from frontend.views.vendor_views.heatmap_tab_view import render_heatmap_tab_view
from frontend.views.vendor_views.list_tab_view import render_vendor_list_tab

def render_vendors_page() -> None:
    """Render the Vendors page with vendor list and management controls."""
    
    st.markdown(get_styles("vendors_page"), unsafe_allow_html=True)

    vendor_title_col, new_vendor_button_col, spacer = st.columns([0.8, 0.1, 0.1])
    with vendor_title_col:
        st.title("🏢 Vendors")
    
    st.divider()

    with new_vendor_button_col:
        if st.button("➕ New Vendor", type="primary", width="stretch", disabled=not current_user_has_permission(Permission.CREATE_VENDORS)):
            create_vendor("New Vendor")
            st.rerun()

    render_vendor_page_tabs()

    if st.session_state.get("current_tab") == "Vendor List":
        render_vendor_list_tab()

    elif st.session_state.get("current_tab") == "Heat Map":
        render_heatmap_tab_view()


def render_vendor_page_tabs() -> None:
    """Render tab buttons for switching between tabs"""

    # Initialize tab variable
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "Vendor List"

    tab1, tab2, tab3, tab4, tab5 = st.columns([0.2, 0.2, 0.2, 0.2, 0.2])

    with tab1:
        type1 = "primary" if st.session_state.current_tab == "Vendor List" else "secondary"

        if st.button("Vendor List", type=type1, width='stretch'):
            st.session_state.current_tab = "Vendor List"
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_tab == "Heat Map" else "secondary"
        
        if st.button("Heat Map", type=type2, width='stretch'):
            st.session_state.current_tab = "Heat Map"
            st.rerun()

    st.divider()