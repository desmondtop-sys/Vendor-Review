import streamlit as st

from defs import Page, Main_Col_Tabs, Vendor_Page_Tabs

from backend.vendor_database import create_vendor, get_all_vendor_models
from backend.permissions import Permission

from frontend.styles import get_styles
from frontend.state_manager import handle_vendor_switch
from frontend.views.shared_components_view import render_logo, render_vendor_selector_button
from frontend.views.login_view import logout
from frontend.auth_helpers import current_user_has_permission

def render_left_sidebar() -> None:
    """Render the complete left sidebar including navigation and report history."""

    # Set styles for the page
    st.markdown(get_styles("left_sidebar"), unsafe_allow_html=True)

    render_logo()
    
    render_user_info()
    
    render_page_selectors()

    render_vendor_selection()

def render_page_selectors() -> None:
    """Render sidebar controls for page navigation and creating a new vendor."""

    st.title("🧭 Navigation")
    
    disabled = st.session_state.get("analysis_in_progress", False)

    # Add a page selector
    if "current_page" not in st.session_state:
        st.session_state.current_page = Page.DASHBOARD.value

    button_types = get_button_types(st.session_state.current_page)

    # Render vendors button for non-client users
    if not current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        if st.button("🏢 Vendor List", width='stretch', type=button_types["vendors"], disabled=disabled):
            st.session_state.current_page = Page.VENDORS.value
            st.session_state.current_tab = Vendor_Page_Tabs.VENDOR_LIST.value

            # Reset vendor tracking to force vendor name reload
            if "_last_vendor_id" in st.session_state:
                del st.session_state["_last_vendor_id"]
            st.rerun()
    
    # Render dashboard button for all users
    if st.button("📊 Analysis Dashboard", width='stretch', type=button_types["dashboard"], disabled=disabled):
        st.session_state.current_page = Page.DASHBOARD.value
        st.session_state.current_tab = Main_Col_Tabs.DASHBOARD.value
        # Reset vendor tracking to force vendor name reload
        if "_last_vendor_id" in st.session_state:
            del st.session_state["_last_vendor_id"]
        st.rerun()

    # Render AI settings button for non-client users
    if not current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        if st.button("⚙️ AI Configuration", width='stretch', type=button_types["settings"], disabled=disabled):
            st.session_state.current_page = Page.SETTINGS.value
            st.session_state.current_tab = None
            st.rerun()

    # If user is admin, show user management button
    if current_user_has_permission(Permission.CONTROL_USERS):
        if st.button("👥 User Management", width='stretch', type=button_types["user_control"], disabled=disabled):
            st.session_state.current_page = Page.USER_CONTROL.value
            st.session_state.current_tab = None
            # Clear any previous user search and role filters when navigating to user management
            st.session_state.user_search = ""
            st.session_state.selected_roles = set()

            # Reset vendor tracking to force vendor name reload
            if "_last_vendor_id" in st.session_state:
                del st.session_state["_last_vendor_id"]
            st.rerun()

    # Add new vendor button
    if not current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        if st.button("➕ New Vendor", width='stretch', type="secondary", disabled=disabled):
            vendor_id = create_vendor("New Vendor")
            
            if vendor_id:
                handle_vendor_switch(vendor_id)

    st.divider()

def render_vendor_selection() -> None:
    """Render vendor list and switch active vendor on selection."""

    st.title("🏢 Vendors")
    vendors = get_all_vendor_models()

    if current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS):
        assigned_vendor_id = st.session_state.get("user_assigned_vendor_id")
        vendors = [vendor for vendor in vendors if vendor.id == assigned_vendor_id]

    if not vendors:
        st.info("No vendors yet.")
        return

    for vendor in vendors:
        render_vendor_selector_button(vendor, key_prefix="sidebar_")

def render_user_info() -> None:
    """Render current user information and logout button."""
    
    # Display user info
    username = st.session_state.get("username", "Guest")
    user_full_name = st.session_state.get("user_full_name")
    user_role = st.session_state.get("user_role")
    
    # User info display
    st.markdown("### 👤 Account Details")
    
    if user_full_name:
        st.markdown(f"**{user_full_name}**")
    else:
        st.markdown(f"**{username}**")
    
    if user_role:
        role_display = user_role.value.capitalize()
        role_icons = {"admin": "🔑", "analyst": "📊", "client": "🏢", "viewer": "👁️"}
        icon = role_icons.get(user_role.value, "👤")
        st.markdown(f"{icon} **{role_display}**")
    
    # Logout button
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        logout()

    st.divider()

def get_button_types(current_page: str) -> dict:
    """Helper function to determine button styles based on the current page."""
    # Default state for all buttons
    default_types = {"dashboard": "secondary", "vendors": "secondary", "settings": "secondary", "user_control": "secondary"}
    
    # Determine which button should be primary based on current page
    if current_page == Page.DASHBOARD.value:
        default_types["dashboard"] = "primary"
    elif current_page == Page.VENDORS.value:        
        default_types["vendors"] = "primary"
    elif current_page == Page.SETTINGS.value:
        default_types["settings"] = "primary"
    elif current_page == Page.USER_CONTROL.value:
        default_types["user_control"] = "primary"
    
    return default_types