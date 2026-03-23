from enum import Enum
from backend.models import UserRole

class Permission(str, Enum):
    """Action permissions for different features."""
    # Report permissions
    VIEW_REPORTS                = "View Reports"
    CREATE_REPORTS              = "Create Reports"
    DELETE_REPORTS              = "Delete Reports"
    SELECT_REPORTS              = "Select Reports"
    DOWNLOAD_REPORTS            = "Download Reports"
    VIEW_SUMMARIES              = "View Summaries"
    VIEW_EVIDENCE               = "View Evidence"

    # Vendor permissions
    CREATE_VENDORS              = "Create Vendors"
    DELETE_VENDORS              = "Delete Vendors"
    SCOPED_VENDOR_ACCESS        = "Scoped Vendor Access"   # Permission for clients - allows access only to their assigned vendor

    # Document permissions
    VIEW_DOCUMENTS              = "View Documents"
    UPLOAD_DOCUMENTS            = "Upload Documents"
    DOWNLOAD_DOCUMENTS          = "Download Documents"
    DELETE_DOCUMENTS            = "Delete Documents"
    VIEW_NDA_DOCUMENTS          = "View NDA Documents"

    # User management permissions
    CONTROL_USERS               = "Control Users"

    # Other permissions
    EDIT_SETTINGS               = "Edit Settings"
    TOGGLE_NDA                  = "Toggle NDA"
    TOGGLE_CONTROL_INCLUSION    = "Toggle Control Inclusion"
    MANAGE_BITSIGHT             = "Manage Bitsight"

# Map roles to their permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.VIEW_REPORTS,
        Permission.CREATE_REPORTS,
        Permission.SELECT_REPORTS,
        Permission.DOWNLOAD_REPORTS,
        Permission.DELETE_REPORTS,
        Permission.VIEW_SUMMARIES,
        Permission.VIEW_EVIDENCE,

        Permission.CREATE_VENDORS,
        Permission.DELETE_VENDORS,

        Permission.VIEW_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_NDA_DOCUMENTS,

        Permission.CONTROL_USERS,

        Permission.EDIT_SETTINGS,
        Permission.TOGGLE_NDA,
        Permission.TOGGLE_CONTROL_INCLUSION,
        Permission.MANAGE_BITSIGHT,
    ],
    UserRole.ANALYST: [
        Permission.VIEW_REPORTS,
        Permission.CREATE_REPORTS,
        Permission.SELECT_REPORTS,

        Permission.VIEW_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,

        Permission.TOGGLE_CONTROL_INCLUSION,
        Permission.MANAGE_BITSIGHT,
    ],
    UserRole.CLIENT: [
        Permission.VIEW_REPORTS,
        Permission.DOWNLOAD_REPORTS,
        Permission.VIEW_SUMMARIES,

        Permission.SCOPED_VENDOR_ACCESS,

        Permission.VIEW_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.VIEW_NDA_DOCUMENTS,
    ],
    UserRole.VIEWER: [
        Permission.VIEW_REPORTS,
    ],
}

def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """Check if a user role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(user_role, [])