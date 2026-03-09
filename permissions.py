from enum import Enum
from backend.models import UserRole

class Permission(str, Enum):
    """Action permissions for different features."""
    # Report permissions
    VIEW_REPORTS                = "view_reports"
    CREATE_REPORTS              = "create_reports"
    DELETE_REPORTS              = "delete_reports"
    SELECT_REPORTS              = "select_reports"
    DOWNLOAD_REPORTS            = "download_reports"
    VIEW_SUMMARIES              = "view_summaries"
    VIEW_EVIDENCE               = "view_evidence"

    # Vendor permissions
    CREATE_VENDORS              = "create_vendors"
    DELETE_VENDORS              = "delete_vendors"
    SCOPED_VENDOR_ACCESS        = "scoped_vendor_access"   # Permission for clients - allows access only to their assigned vendor

    # Document permissions
    VIEW_DOCUMENTS              = "view_documents"
    UPLOAD_DOCUMENTS            = "upload_documents"
    DOWNLOAD_DOCUMENTS          = "download_documents"
    DELETE_DOCUMENTS            = "delete_documents"
    VIEW_NDA_DOCUMENTS          = "view_nda_documents"

    # Other permissions
    EDIT_SETTINGS               = "edit_settings"
    TOGGLE_NDA                  = "toggle_nda"
    TOGGLE_CONTROL_INCLUSION    = "toggle_control_inclusion"
    MANAGE_BITSIGHT             = "manage_bitsight"

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