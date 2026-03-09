"""Login page for user authentication."""

import streamlit as st
from backend.user_database import authenticate_user
from backend.permissions import has_permission, Permission
from backend.config_manager import get_ai_instructions, get_ai_requirements, get_threshold_settings
from frontend.styles import get_styles


def render_login_page() -> None:
    """Render the login page with authentication form."""
    
    # Get styles for the login page
    st.markdown(get_styles("login_page"), unsafe_allow_html=True)
    
    # Create centered container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-header">', unsafe_allow_html=True)
        st.title("🔐 Vendor Evaluator")
        st.subheader("Sign In")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                key="login_username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="login_password"
            )
            
            submit_button = st.form_submit_button("Sign In", type="primary")
            
            if submit_button:
                if not username or not password:
                    st.error("⚠️ Please enter both username and password")
                else:
                    # Attempt authentication
                    user = authenticate_user(username, password)
                    
                    if user:
                        # Access gates are evaluated in order:
                        # 1) account active, 2) scoped users must be linked to a vendor,
                        # 3) on success hydrate session + cached settings.
                        if not user.is_active:
                            st.error("⚠️ Your account has been deactivated...")
                        elif has_permission(user.role, Permission.SCOPED_VENDOR_ACCESS) and user.assigned_vendor_id is None:
                            st.error("⚠️ Your client account is not linked to a vendor yet. Please contact an administrator.")
                        else:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.session_state.user_role = user.role  # Store enum
                            st.session_state.user_assigned_vendor_id = user.assigned_vendor_id
                            st.session_state.user_email = user.email
                            st.session_state.user_full_name = user.full_name
                            
                            # Cache settings at login
                            st.session_state.cached_ai_instructions = get_ai_instructions()
                            st.session_state.cached_ai_requirements = get_ai_requirements()
                            st.session_state.cached_threshold_settings = get_threshold_settings()
                            
                            st.success(f"✅ Welcome {user.full_name}!")
                            st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
        
        # Additional info
        st.markdown("---")
        st.markdown(
            "<p style='text-align: center; color: #666; font-size: 0.9em;'>"
            "Contact your administrator for account access"
            "</p>",
            unsafe_allow_html=True
        )


def logout() -> None:
    """Clear authentication session state and return to login page."""
    
    # Clear all authentication-related session state
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.user_email = None
    st.session_state.user_full_name = None
    st.session_state.user_role = None
    st.session_state.user_assigned_vendor_id = None
    
    # Clear cached settings snapshot
    st.session_state.cached_ai_instructions = None
    st.session_state.cached_ai_requirements = None
    st.session_state.cached_threshold_settings = None
    
    # Prevent data leakage between user sessions
    keys_to_clear = [
        'active_vendor_id',
        'active_report',
        'simulation_report',
        'live_pdf_data',
        '_last_vendor_id',
        'vendor_name_text_area'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.rerun()