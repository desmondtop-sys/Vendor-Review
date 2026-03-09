import streamlit as st
from pathlib import Path

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
        st.session_state.current_page = "Dashboard"

    # Set styles for the buttons based on the current page
    if st.session_state.current_page == "Dashboard":
        type1 = "primary"
        type2 = "secondary"
        type3 = "secondary"
    elif st.session_state.current_page == "Vendors":        
        type1 = "secondary"
        type2 = "primary"
        type3 = "secondary"
    elif st.session_state.current_page == "Settings":
        type1 = "secondary"
        type2 = "secondary"
        type3 = "primary"

    is_scoped_vendor_user = current_user_has_permission(Permission.SCOPED_VENDOR_ACCESS)

    if not is_scoped_vendor_user:
        if st.button("🏢 Vendor List", width='stretch', type=type2, disabled=disabled):
            st.session_state.current_page = "Vendors"
            st.session_state.current_tab = "Vendor List"
            # Reset vendor tracking to force vendor name reload
            if "_last_vendor_id" in st.session_state:
                del st.session_state["_last_vendor_id"]
            st.rerun()
    
    if st.button("📊 Analysis Dashboard", width='stretch', type=type1, disabled=disabled):
        st.session_state.current_page = "Dashboard"
        st.session_state.current_tab = "Dashboard"
        # Reset vendor tracking to force vendor name reload
        if "_last_vendor_id" in st.session_state:
            del st.session_state["_last_vendor_id"]
        st.rerun()


    if not is_scoped_vendor_user:
        if st.button("⚙️ AI Configuration", width='stretch', type=type3, disabled=disabled):
            st.session_state.current_page = "Settings"
            st.session_state.current_tab = None
            st.rerun()

    # Add new vendor button
    if not is_scoped_vendor_user:
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