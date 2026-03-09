from enum import Enum

from pydantic import BaseModel
from typing import List, Optional

class SecurityControl(BaseModel):
    name: str                   # Short identifier/name for the requirement
    requirement: str            # Full description of what we want from the vendor
    status: int                 # 1 for Pass, 0 for Fail
    weight: int                 # The weight of the control - how much we care about this requirement
    must_pass: bool = False     # A requirement that absolutely cannot be missing
    priority: int = 3           # Priority level (1-5), where 5 is highest priority
    evidence: str               # The AI's reasoning behind their Pass/Fail score

class AIEvaluation(BaseModel):
    vendor_name: str                    # Vendor name
    controls: List[SecurityControl]     # A list of requirements that are either met or not met
    summary: str                        # Summary of the findings

class Report(BaseModel):
    id: Optional[int] = None
    prompt: str                         # The prompt that was used to generate this report
    vendor_name: str                    # Vendor name
    controls: List[SecurityControl]     # A list of requirements that are either met or not met
    summary: str                        # Summary of the findings
    overall_score: int
    possible_score: int
    file_names: List[str] = []          # List of associated documents
    storage_path: Optional[str] = None  # Path to the folder
    excluded_names: List[str] = []      # List of control names excluded from security score calculations
    run_number: Optional[int] = None    # Report version number (v1, v2, v3, etc) for this vendor
    version: Optional[int] = None       # Optimistic lock version - incremented on each save to detect concurrent edits
    timestamp: Optional[str] = None     # When this report was created

class Vendor(BaseModel):
    id: Optional[int] = None
    name: str
    nda_signed: bool = False
    active_report_id: Optional[int] = None
    max_run_number: int = 0
    bitsight_company_guid: Optional[str] = None
    bitsight_company_name: Optional[str] = None
    bitsight_rating: Optional[int] = None
    bitsight_rating_date: Optional[str] = None
    created_at: Optional[str] = None

class UserRole(str, Enum):
    ADMIN = "admin"              # Full system access, manage users/vendors
    ANALYST = "analyst"          # Can view reports, create reports
    CLIENT = "client"            # Can only see their own vendor's info
    VIEWER = "viewer"            # Read-only access to reports

class User(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    assigned_vendor_id: Optional[int] = None        # For client users, which vendor they are associated with
    is_active: bool = True
    created_at: Optional[str] = None
    last_login: Optional[str] = None