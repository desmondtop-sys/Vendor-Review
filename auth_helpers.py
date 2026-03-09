import streamlit as st
from backend.models import UserRole
from backend.permissions import has_permission, Permission

def get_current_user_role() -> UserRole | None:
    """Get current logged-in user's role."""

    return st.session_state.get("user_role")


def current_user_has_permission(permission: Permission) -> bool:
    """Check if current user has a specific permission.
    
    Args:
        permission: The permission to check
        
    Returns:
        True if user has the permission, False otherwise
    """
    
    user_role = get_current_user_role()
    if not user_role:
        return False
    
    return has_permission(user_role, permission)


def current_user_is(role: UserRole) -> bool:
    """Check if current user is specifically a given role.
    
    Args:
        user_role: The UserRole enum value to check against
        
    Returns:
        True if user is the specified role, False otherwise
    """
    current_user_role = get_current_user_role()
    if not current_user_role:
        return False
    return current_user_role == role