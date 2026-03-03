"""Streamlit UI stylesheet definitions for all pages and components.

This module provides CSS styling functions that are imported and rendered
across the application to maintain consistent appearance and formatting.
"""

def primary_buttons() -> str:
    """Return shared primary-button CSS overrides.

    Returns:
        str: HTML style block for Streamlit primary button colors.
    """

    return """
        <style>
        /* Primary Buttons (Slate Blue) */
        div.stButton > button[kind="primary"] {
            background-color: #4A6984 !important;
            border-color: #4A6984 !important;
        }
        </style>
        """

def left_sidebar_style() -> str:
    """Return CSS specific to the left sidebar layout.

    Returns:
        str: HTML style block for sidebar spacing.
    """

    style = """
        <style>
        
        /* Hide sidebar collapse button */
        button[kind="headerNoPadding"] {
            display: none !important;
        }
        
        /* Target markdown elements to remove top margin */
        section[data-testid="stSidebar"] > div > div > div > div:first-child {
            margin-top: -4rem !important;
        }
        
        /* Sidebar vertical spacing */
        hr {
            margin-top: 1.0rem !important;
            margin-bottom: 1.0rem !important;
        }
        </style>
        """
    
    return style

def vendor_title_style() -> str:
    """Return CSS for the vendor title section at the top of the dashboard."""

    style = """
        <style>

        /* Style the text area */
        div[data-testid="stTextArea"] textarea {
            font-size: clamp(1.25rem, 2vw, 1.9rem) !important;
            font-weight: 700 !important;
            min-height: 70px !important;
            height: clamp(70px, 9vw, 98px) !important;
            padding-top: clamp(14px, 2.4vw, 35px) !important;
            line-height: 1.15 !important;
            resize: none !important;
        }

        /* Style the 'Vendor:' text */
        .vendor-title {
            margin-top: clamp(20px, 1.8vw, 28px) !important;
            font-size: clamp(2.0rem, 3.0vw, 2.0rem) !important;
            font-weight: 700 !important;
        }
        </style>
        """
    style += primary_buttons()
    return style


def dashboard_style() -> str:
    """Return dashboard-specific CSS for controls and typography.

    Returns:
        str: HTML style block for dashboard UI elements.
    """

    style = """
        <style>

        /* Checkbox color */
        [data-testid="stCheckbox"] label span:first-child:has(+ input[type="checkbox"]:checked),
        [data-testid="stCheckbox"] input[type="checkbox"]:checked + span {
            background-color: #4A6984 !important;
            border-color: #4A6984 !important;
        }

        /* Checkbox Size and Position */
        [data-testid="stCheckbox"] {
            transform: scale(1.5);
            margin-top: 5px !important;
            margin-left: 5px !important;
        }

        @media (max-width: 1200px) {
            [data-testid="stCheckbox"] {
                transform: scale(1.2);
                margin-top: 2px !important;
                margin-left: 2px !important;
            }
        }
        
        /* PDF Download button style */
        div.st-key-report_download_container [data-testid="stDownloadButton"] > button {
             background-color: #4A6984 !important;
             border-color: #4A6984 !important;
             color: white !important;
        }
        /* Unsaved data button (Red) */
        div.stButton > button[kind="tertiary"] {
            background-color: #ff4b4b !important;
            color: white !important;
            border: 1px solid #ff4b4b !important;
        }
        </style>
        """
    style += primary_buttons()
    return style

def analysis_style() -> str:
    """Return CSS used by the analysis tools page.

    Returns:
        str: HTML style block for analysis-page checkbox layout and colors.
    """
    
    style = """
        <style>

        /* Vendor label styling for analysis page */
        .vendor-label {
            font-size: inherit !important;
            font-weight: inherit !important;
            margin-top: 0 !important;
        }       

        /* Checkbox color */
        [data-testid="stCheckbox"] label span:first-child:has(+ input[type="checkbox"]:checked),
        [data-testid="stCheckbox"] input[type="checkbox"]:checked + span {
            background-color: #4A6984 !important;
            border-color: #4A6984 !important;
        }

        /* Checkbox position */
        [data-testid="stCheckbox"] {
            transform: scale(1.5);
            margin-left: 45px !important;  /* Pushes the box to the right */
        }

        /* Reduce size and spacing on smaller windows */
        @media (max-width: 1200px) {
            [data-testid="stCheckbox"] {
                transform: scale(1.2);
                margin-left: 15px !important;
            }
        }
        </style>
        """
    
    style += primary_buttons()
    return style

def right_sidebar_style() -> str:
    """Return CSS specific to the right sidebar.

    Returns:
        str: HTML style block for right-sidebar styling.
    """

    style = ""

    style += primary_buttons()
    return style

def settings_page_style() -> str:
    """Return CSS used by the AI settings page.

    Returns:
        str: HTML style block for settings-page layout and widget styling.
    """

    style = """
        <style>        
        div[data-testid="stTextArea"] textarea {
            font-family: monospace !important;
            resize: none !important;
        }

        /* Scale settings content down on smaller windows without causing horizontal overflow */
        @media (max-width: 1600px) {
            section.main .block-container {
                zoom: 0.94;
            }
        }

        @media (max-width: 1360px) {
            section.main .block-container {
                zoom: 0.88;
            }
        }

        @media (max-width: 1180px) {
            section.main .block-container {
                zoom: 0.82;
            }
        }

        /* Adjust spacings */
        h3 {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
        }

        /* Keep checkbox labels on one line in tighter layouts */
        [data-testid="stCheckbox"] label p {
            white-space: nowrap !important;
        }

        /* Checkbox color */
        [data-testid="stCheckbox"] label span:first-child:has(+ input[type="checkbox"]:checked),
        [data-testid="stCheckbox"] input[type="checkbox"]:checked + span {
            background-color: #4A6984 !important;
            border-color: #4A6984 !important;
        }

        /* Unsaved data button (Red) */
        div.stButton > button[kind="tertiary"] {
            background-color: #ff4b4b !important;
            color: white !important;
            border: 1px solid #ff4b4b !important;
        }
        </style>
        """
    
    style += primary_buttons()
    return style

def vendors_page_style() -> str:
    style = ""
    style += primary_buttons()
    return style

def heatmap_style() -> str:
    """Return CSS used by the vendor heatmap tab."""

    style = """
        <style>
        .heatmap-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        .heatmap-table {
            border-collapse: collapse;
            font-size: 14px;
            width: max-content;
            min-width: 100%;
        }
        .heatmap-table th,
        .heatmap-table td {
            padding: 6px 8px;
            text-align: center;
            border: 1px solid #ddd;
            white-space: nowrap;
        }
        .heatmap-table th {
            background-color: #262730;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        .heatmap-table th.vendor-col {
            text-align: left;
            min-width: 140px;
            width: 140px;
            position: sticky;
            left: 0;
            z-index: 15;
            padding: 6px 8px;
        }
        .heatmap-table th.control-col {
            font-size: 11px;
            width: 36px;
            min-width: 36px;
            max-width: 36px;
            height: 36px;
            padding: 0;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .heatmap-table th.score-col {
            background-color: #262730;
            color: white;
            position: sticky;
            right: 0;
            z-index: 12;
            min-width: 140px;
            width: 140px;
            padding: 6px 8px;
        }
        .heatmap-table td.vendor-name {
            text-align: left;
            font-weight: 500;
            background-color: #e9ecef;
            color: #212529;
            position: sticky;
            left: 0;
            z-index: 5;
            padding: 6px 8px;
        }
        .heatmap-table td.score-cell {
            font-weight: 600;
            font-size: 14px;
            background-color: #e9ecef;
            color: #212529;
            position: sticky;
            right: 0;
            z-index: 4;
            min-width: 140px;
            width: 140px;
            padding: 6px 8px;
        }
        .heatmap-table td.control-cell {
            width: 36px;
            min-width: 36px;
            max-width: 36px;
            height: 36px;
            padding: 0;
            line-height: 36px;
        }
        .heatmap-table tr.summary-row td {
            background-color: #262730;
            color: #ffffff;
            font-weight: 600;
        }
        .heatmap-table td.summary-cell {
            font-size: 11px;
            line-height: 16px;
        }
        .heatmap-table td.summary-label {
            font-weight: 700;
        }
        .cell-pass {
            background-color: #28a745;
            color: white;
            font-weight: 500;
        }
        .cell-fail {
            background-color: #dc3545;
            color: white;
            font-weight: 500;
        }
        .cell-missing {
            background-color: #6c757d;
            color: white;
            font-weight: 500;
        }
        </style>
        """
    return style

def analysis_loading_style() -> str:
    """Return CSS for the full-screen analysis loading spinner.

    Returns:
        str: HTML style block for the loading screen overlay.
    """

    style = """
        <style>
        /* Adjust text size */
        .stSpinner p {
            font-size: 18px !important;
            font-weight: 500;
            color: #ffffff;
        }
        </style>
        """
    return style

def login_page_style() -> str:
    """Return CSS for the login and registration pages."""

    style = """
        <style>
        .login-container {
            max-width: 400px;
            margin: auto;
            padding-top: 100px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        /* Form submit button full width */
        div[data-testid="stFormSubmitButton"] > button {
            width: 100%;
            margin-top: 1rem;
            background-color: #4A6984 !important;
            border-color: #4A6984 !important;
        }
        /* Regular buttons full width */
        .stButton > button {
            width: 100%;
            margin-top: 1rem;
        }
        </style>
    """

    style += primary_buttons()

    return style

_PAGE_STYLES = {
    "left_sidebar": left_sidebar_style,
    "vendor_title": vendor_title_style,
    "dashboard": dashboard_style,
    "analysis": analysis_style,
    "assets": dashboard_style,
    "right_sidebar": right_sidebar_style,
    "ai_settings_page": settings_page_style,
    "vendors_page": vendors_page_style,
    "heatmap": heatmap_style,
    "analysis_loading": analysis_loading_style,
    "login_page": login_page_style
}

def get_styles(page: str) -> str:
    """Return combined global and page-specific CSS.

    Args:
        page (str): Page key used to select a style builder from `_PAGE_STYLES`.

    Returns:
        str: Final HTML style block containing global and page CSS.
    """

    styles = ""

    # Universal styles
    styles += """
        <style>   

        /* Edit margins around entire screen to reduce blank space */
        .block-container {
            padding-top: clamp(1.25rem, 3vw, 5rem);
            padding-bottom: clamp(1.25rem, 3vw, 5rem);
            padding-left: clamp(1rem, 3vw, 5rem);
            padding-right: clamp(1rem, 3vw, 5rem);
        }

        /* Globally hide anchors for headers */
        .stMarkdown h3 a {
            display: none !important;
        }

        /* Reduce main header height */
        .st-key-main_title h1 {
            font-size: clamp(1.3rem, 2vw, 2rem);
            line-height: 1.1;
            margin: 0 0 0 0;
        }

        /* Main dashboard shell (center + right panel) */
        div.st-key-app_shell div.app-shell-divider {
            border-left: 1px solid #31333F;
            height: 100vh;
            margin-left: 5px;
        }
        </style>
        """
    
    page_style = _PAGE_STYLES.get(page, lambda: "")
    return styles + page_style()