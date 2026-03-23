import streamlit as st

from defs import SECONDARY_TEXT_COLOR

from backend.report_utils import check_critical_failure, get_security_score_by_id
from backend.vendor_database import save_report, get_vendor_model_by_id, get_report_by_id
from backend.permissions import Permission
from backend.models import DataType

from frontend.styles import get_styles
from frontend.views.shared_components_view import render_delete_vendor_button, render_nda_toggle_button
from frontend.auth_helpers import current_user_has_permission


def _save_report_safely(report) -> bool:
    """Helper to save report with error handling and validation.
    
    Returns True if successful, False if report was deleted or error occurred.
    Automatically reruns on error.
    """
    # Validate record existence first because another user may have deleted it while this client still has stale in-memory state.
    if not get_report_by_id(report.id):
        st.error("This report was deleted. Reloading...")
        st.session_state.active_report = None
        st.rerun()
        return False
    
    # Save can raise version conflict errors when concurrent edits occur.
    try:
        save_report(report)
        return True
    except RuntimeError as e:
        st.error(str(e))
        st.rerun()
        return False


def render_dashboard() -> None:
    """Render dashboard components for summary, requirements, and deletion actions."""

    st.markdown(get_styles("dashboard"), unsafe_allow_html=True)

    render_report_summary()

    render_requirements()
    
    st.divider()

    vendor_id = st.session_state.get("active_vendor_id")
    if vendor_id:
        vendor = get_vendor_model_by_id(vendor_id)
        
        # Vendor may have been deleted by another user
        if not vendor:
            st.error("⚠️ This vendor no longer exists. It may have been deleted.")
            return

        spacer1, delete_col, spacer2 = st.columns([0.35, 0.3, 0.35])
        with delete_col:
            render_delete_vendor_button(vendor)

def render_report_summary() -> None:
    """Render vendor summary header, security score, and executive summary panel."""
    
    # Report header row (NDA toggle appears right of report version)
    version_col, nda_col = st.columns([0.7, 0.3])

    # Print report version and vendor name
    with version_col:

        report = st.session_state.active_report
    
        run_number = report.run_number if report else "0"
        st.subheader(f"**Report Version:** _v{run_number}_")

    # Render NDA toggle button in header for easy access
    with nda_col:

        vendor = None
        vendor_id = st.session_state.get("active_vendor_id")
        if vendor_id:
            vendor = get_vendor_model_by_id(vendor_id)

        if vendor:
            render_nda_toggle_button(vendor)

    date_col, data_type_col1, data_type_col2 = st.columns([0.55, 0.15, 0.3])

    with date_col:
        # Print report date
        timestamp = report.timestamp[:10] if report and report.timestamp else "Unknown"
        st.subheader(f"**Date:** _{timestamp}_")

    # Display and edit data type
    with data_type_col1:
        st.subheader("**Data Type:**")
    
    # if user has permissions to edit, show dropdown. Otherwise just show text.
    if report and current_user_has_permission(Permission.CREATE_REPORTS):
        with data_type_col2:
            selected_type = st.selectbox(
                "Select data sensitivity level",
                options=[dt.value for dt in DataType],
                index=[dt.value for dt in DataType].index(report.data_type.value) if report.data_type else 0,
                label_visibility="collapsed",
                key=f"data_type_select_{report.id}"
            )

            if selected_type != report.data_type.value:
                report.data_type = DataType(selected_type)
                if _save_report_safely(report):
                    st.success("Data type updated!")
                    st.rerun()       
    elif report:
        with data_type_col2:
            st.subheader(f"_{report.data_type.value if report.data_type else 'Public'}_")

    # Calculate security score and load summary
    if report is None:
        score = 0
        possible = 0
        critical_failure = False

        summary = "No report loaded. Please upload documents and generate a report to see the executive summary here."
    else:
        score, possible, critical_failure = get_security_score_by_id(report.id)

        summary = report.summary

    if current_user_has_permission(Permission.VIEW_SUMMARIES):
        st.subheader("Executive Summary")
        st.info(summary)
    else:
        st.info("🔒 Executive summary is restricted to administrators only.")

    if critical_failure:
        st.error("🛑 CRITICAL FAILURE: One or more 'Must Pass' requirements or sensitive-data critical controls were not met.")

def render_requirements() -> None:
    """Render requirement-level status, evidence, weight, and include toggles."""
    header_col, include_col = st.columns([0.9, 0.1])
        
    with header_col:
        st.subheader("Requirement Breakdown")

    with include_col:
        st.markdown(
            f"""<p style="
            font-size: 14px;
            font-weight: 600;
            margin-top: 35px;
            margin-bottom: 0px;
            text-align: center;
            ">Include</p>""", 
            unsafe_allow_html=True
        )
    
    report = st.session_state.active_report    
    controls = report.controls if report else []

    for control in controls:
        expander_col, weight_col, check_col = st.columns([0.9, 0.06, 0.04])

        with expander_col:
            if control.status == 1:
                status_icon = "✅ Pass" 
            elif check_critical_failure(control, report.data_type):
                # Must-pass failures are elevated to critical regardless of score.
                status_icon = "‼️ CRITICAL FAIL"
            else:
                status_icon = "❌ Fail"

            with st.expander(f"{status_icon} - {control.name}"):
                st.write(f"**Requirement Description:** {control.requirement}")

                st.divider()
                
                if current_user_has_permission(Permission.VIEW_EVIDENCE):
                    st.write(f"**Evidence Found:** {control.evidence}")
                else:
                    # Keep requirement visibility for scoped users while hiding sensitive extracted evidence.
                    st.caption("🔒 Evidence view is restricted to administrators only.")

        with weight_col:
            st.markdown(
                f"""
                <div style=
                "margin-top: 7px; 
                font-weight: 600; 
                color: {SECONDARY_TEXT_COLOR}; 
                text-align: right; 
                white-space: nowrap; 
                padding-right: 0px; 
                padding-left: 0px;"
                >
                    {control.weight} pts
                </div>
                """, 
                unsafe_allow_html=True
            )
        
        # Create a checkbox to toggle each requirement. Turning off will exclude the control from the Security Score calculation
        with check_col:
            
            # Create checkbox
            is_active = st.checkbox(
                "Include", 
                value=(control.name not in report.excluded_names),
                key=f"check_{control.name}_{report.id}",
                label_visibility="collapsed", 
                disabled=not current_user_has_permission(Permission.TOGGLE_CONTROL_INCLUSION),
            )
    
            # Logic to update the object and database directly
            if not is_active and control.name not in report.excluded_names:
                report.excluded_names.append(control.name)
                if _save_report_safely(report):
                    st.rerun()
            elif is_active and control.name in report.excluded_names:
                report.excluded_names.remove(control.name)
                if _save_report_safely(report):
                    st.rerun()