from enum import Enum
from backend.models import UserRole

class Permission(str, Enum):
    """Action permissions for different features."""
    VIEW_REPORTS = "view_reports"
    CREATE_REPORTS = "create_reports"
    MANAGE_VENDORS = "manage_vendors"
    MANAGE_USERS = "manage_users"
    DOWNLOAD_DOCUMENTS = "download_documents"
    DELETE_REPORTS = "delete_reports"

# Map roles to their permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.VIEW_REPORTS,
        Permission.CREATE_REPORTS,
        Permission.MANAGE_VENDORS,
        Permission.MANAGE_USERS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.DELETE_REPORTS,
    ],
    UserRole.ANALYST: [
        Permission.VIEW_REPORTS,
        Permission.CREATE_REPORTS,
        Permission.MANAGE_VENDORS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.DELETE_REPORTS,
    ],
    UserRole.VENDOR_CONTACT: [
        Permission.VIEW_REPORTS,
        Permission.DOWNLOAD_DOCUMENTS,
    ],
    UserRole.VIEWER: [
        Permission.VIEW_REPORTS,
    ],
}

def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if a user role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, [])

def has_any_permission(user_role: UserRole, permissions: list[Permission]) -> bool:
    """Check if user has any of the specified permissions."""
    return any(has_permission(user_role, perm) for perm in permissions)