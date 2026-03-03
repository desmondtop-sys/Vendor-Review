import streamlit as st
from backend.models import UserRole
from backend.permissions import has_permission, Permission

def get_current_user_role() -> UserRole | None:
    """Get current logged-in user's role."""
    return st.session_state.get("user_role")

def require_permission(permission: Permission, error_msg: str = None) -> bool:
    """Check if current user has permission. Show error and stop if not."""
    user_role = get_current_user_role()
    if not user_role or not has_permission(user_role, permission):
        st.error(error_msg or f"❌ Permission denied. Required: {permission}")
        st.stop()
    return True

def require_role(allowed_roles: list[UserRole]) -> bool:
    """Check if user has one of the allowed roles."""
    user_role = get_current_user_role()
    if user_role not in allowed_roles:
        st.error(f"❌ Access denied. Required role: {', '.join(r.value for r in allowed_roles)}")
        st.stop()
    return True