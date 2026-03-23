
from enum import Enum

# Target summed weight for requirements
TARGET_WEIGHT = 1000

# Priority levels for requirements - used in weight calculations and display
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
DEFAULT_WEIGHT = 50

# Threshold Defaults
DEFAULT_PASS_THRESHOLD = 80
DEFAULT_FAIL_THRESHOLD = 50

# Controls
PASS = 1
FAIL = 0

# User Database
MAX_RETRIES = 5
BASE_DELAY = 0.1


# =============
# COLOR PALETTE
# =============

# Pass/Good Status (Green)
PASS_BACKGROUND_COLOR = "#d4edda"
PASS_TEXT_COLOR = "#155724"
PASS_CHART_COLOR = "#24A372"

# Review/Warning Status (Yellow/Orange)
REVIEW_BACKGROUND_COLOR = "#fff3cd"
REVIEW_TEXT_COLOR = "#856404"

# Fail/Error Status (Red)
FAIL_BACKGROUND_COLOR = "#f8d7da"
FAIL_TEXT_COLOR = "#721c24"
FAIL_CHART_COLOR = "#a04e52"


# Secondary/Muted Text Color
SECONDARY_TEXT_COLOR = "#5D7B93"

# Divider/Border Color
COLOR_DIVIDER = "#31333F"

# Info Box/Highlight Background
INFO_BACKGROUND_COLOR = "#E8F2FF"

# Info Box/Highlight Text
INFO_TEXT_COLOR = "#2B4A6F"


# Navigation tabs for the main application.
class Main_Col_Tabs(str, Enum):
    DASHBOARD = "Dashboard"
    ANALYSIS_TOOLS = "Analysis Tools"
    ASSETS = "Assets"
    REPORT_HISTORY = "Report History"
    COMPARE_REPORTS = "Compare Reports"

class Vendor_Page_Tabs(str, Enum):
    VENDOR_LIST = "Vendor List"
    HEAT_MAP = "Heat Map"

# Navigation pages for the main application.
class Page(str, Enum):
    DASHBOARD = "Dashboard"
    VENDORS = "Vendors"
    SETTINGS = "Settings"
    USER_CONTROL = "User Control"

# Document requirement types for client uploads.
class Requirement(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    REDUNDANT_WITH_SOC2 = "redundant_with_soc2"