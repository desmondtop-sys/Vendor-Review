"""Side-by-side report comparison view for analyzing vendor security assessments."""

import streamlit as st

from defs import FAIL, PASS

from backend.vendor_database import generate_vendor_report_from_db, get_all_vendor_reports, get_vendor_model_by_id
from backend.report_utils import calculate_score
from backend.permissions import Permission

from frontend.views.shared_components_view import render_vertical_divider
from frontend.utils import get_badge_styles
from frontend.auth_helpers import current_user_has_permission


def render_compare_reports() -> None:
    """Render the compare reports view for analyzing historical reports side-by-side."""

    st.subheader("📊 Compare Reports")

    vendor_id = st.session_state.active_vendor_id
    
    # Validate that the vendor still exists
    vendor = get_vendor_model_by_id(vendor_id)
    if vendor is None:
        st.error("⚠️ This vendor no longer exists. It may have been deleted.")
        return
    
    reports = get_all_vendor_reports(vendor_id)
    if not reports:
        st.info("No reports available yet. Run an analysis to generate reports for comparison.")
        return

    render_dropdowns(reports)

    st.divider()

    # Generate the selected reports
    left_report = reports[st.session_state.compare_left_report_idx]
    right_report = reports[st.session_state.compare_right_report_idx]
    left_report_obj = generate_vendor_report_from_db(left_report)
    right_report_obj = generate_vendor_report_from_db(right_report)

    # Render the two report selectors
    report1, divider_col, report2 = st.columns([0.5, 0.01, 0.5])

    with report1:
        render_report_description(left_report_obj, "Report 1")

    with divider_col:
        render_vertical_divider("40vh")

    with report2:
        render_report_description(right_report_obj, "Report 2")

    # Render the titles of the reports
    title1, spacer, title2 = st.columns([0.39, 0.22, 0.39])
    
    with title1:
        render_report_title(left_report_obj)

    with title2:
        render_report_title(right_report_obj)

    # Render the controls and comparisons
    controls1, comparison, controls2 = st.columns([0.39, 0.22, 0.39])
    
    with controls1:
        render_report_controls_comparison(left_report_obj, right_report_obj, is_left=True)

    with comparison:
        render_comparisons(left_report_obj, right_report_obj)

    with controls2:
        render_report_controls_comparison(right_report_obj, left_report_obj, is_left=False)

def render_dropdowns(reports: list) -> None:
    """Render the report selection dropdowns for the compare reports view.
    
    Args:
        reports: List of raw database report rows
    """
    # Initialize session state for selected reports if not exists
    if "compare_left_report_idx" not in st.session_state:
        st.session_state.compare_left_report_idx = 0
    if "compare_right_report_idx" not in st.session_state:
        st.session_state.compare_right_report_idx = min(1, len(reports) - 1)   # Get the second report if it exists, otherwise default to the first report

    # Create report options for dropdown using raw database data (no need to generate full report objects)
    report_options = []
    for idx, report in enumerate(reports):
        # Use scores directly from the database row instead of generating the full report object
        score = report["overall_score"]
        possible = report["possible_score"]
        
        # Extract the date from timestamp (remove time portion)
        report_date = report["timestamp"] if report["timestamp"] else "Unknown Date"
        if " " in report_date:
            report_date = report_date.split(" ")[0]  # Take only the date part
        
        # Get version/run number
        run_number = report["run_number"] if report["run_number"] else "N/A"
        
        if possible > 0:
            score_pct = (score / possible) * 100
            option_text = f"v{run_number} | {report_date} | Score: {score}/{possible} ({score_pct:.1f}%)"
        else:
            option_text = f"v{run_number} | {report_date} | Pending"
        
        report_options.append(option_text)

    # Dropdown row at the top
    dropdown_col1, dropdown_col2 = st.columns(2, gap="medium")
    
    with dropdown_col1:
        left_idx = st.selectbox(
            "📌 Report 1:",
            range(len(report_options)),
            format_func=lambda x: report_options[x],
            key="selectbox_left",
            index=st.session_state.compare_left_report_idx,
        )
        st.session_state.compare_left_report_idx = left_idx
    
    with dropdown_col2:
        right_idx = st.selectbox(
            "📌 Report 2:",
            range(len(report_options)),
            format_func=lambda x: report_options[x],
            key="selectbox_right",
            index=st.session_state.compare_right_report_idx,
        )
        st.session_state.compare_right_report_idx = right_idx

def render_report_description(report_obj, label: str) -> None:
    """Render the report description section.
    
    Args:
        report_obj: Generated VendorReport object
        label: Display label (e.g., "Report 1" or "Report 2")
    """
    st.markdown(f"### {label}")
            
    score, possible, critical_failure = calculate_score(report_obj)
         
    # Display summary section                
    status, color, text_color = get_badge_styles(score, possible, critical_failure)
           
    if possible > 0:
        score_pct = (score / possible) * 100
        st.markdown(
            f'<div style="background-color: {color}; color: {text_color}; padding: 10px; border-radius: 8px; margin-bottom: 12px;">'
            f'<strong>Score:</strong> {score}/{possible} ({score_pct:.1f}%) - {status}</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("Report pending analysis")
            
    # Summary text
    if report_obj.summary:
        if current_user_has_permission(Permission.VIEW_SUMMARIES):
            st.markdown(f"**Findings:** {report_obj.summary}")
        else:
            st.caption("🔒 Executive summary is restricted to administrators only.")


def render_report_title(report_obj) -> None:
    """Render the report title and metadata.
    
    Args:
        report_obj: Generated VendorReport object
    """
    # Controls section
    st.subheader("Security Controls")
            
    if report_obj.controls:
        passed_count = sum(1 for c in report_obj.controls if c.status == 1)
        failed_count = len(report_obj.controls) - passed_count
        st.caption(f"{passed_count} Passed | {failed_count} Failed")
    

def render_report_controls(report_obj) -> None:
    """Render the report controls section.
    
    Args:
        report_obj: Generated VendorReport object
    """
    # Display controls in a compact format
    with st.container():
        for control in report_obj.controls:
            status_icon = "✅" if control.status == 1 else "❌"
            
            with st.expander(f"{status_icon} {control.name} ({control.weight})", expanded=False):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("Status", "Pass" if control.status == 1 else "Fail")
                    st.metric("Weight", control.weight)
                with col2:
                    if current_user_has_permission(Permission.VIEW_EVIDENCE):
                        st.write(f"**Evidence:** {control.evidence}")
                    else:
                        st.caption("🔒 Evidence view is restricted to administrators only.")


def render_report_controls_comparison(report_obj, other_report_obj, is_left: bool) -> None:
    """Render the report controls section for comparison view, including placeholders for missing controls.
    
    Args:
        report_obj: Generated VendorReport object for this side
        other_report_obj: Generated VendorReport object for the opposite side
        is_left: True if this is the left column, False if right
    """
    # Get unique control names from both reports
    report_control_names = {c.name for c in report_obj.controls}
    other_control_names = {c.name for c in other_report_obj.controls}
    all_control_names = sorted(report_control_names | other_control_names)
    
    # Display controls in order
    with st.container():
        for control_name in all_control_names:
            control = next((c for c in report_obj.controls if c.name == control_name), None)
            other_control = next((c for c in other_report_obj.controls if c.name == control_name), None)
            
            if control is not None:
                # Control exists in this report
                status_icon = "✅" if control.status == 1 else "❌"
                
                with st.expander(f"{status_icon} {control.name} ({control.weight})", expanded=False):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.metric("Status", "Pass" if control.status == 1 else "Fail")
                        st.metric("Weight", control.weight)
                    with col2:
                        if current_user_has_permission(Permission.VIEW_EVIDENCE):
                            st.write(f"**Evidence:** {control.evidence}")
                        else:
                            st.caption("🔒 Evidence view is restricted to administrators only.")
            else:
                # Control exists in other report but not this one - show blank placeholder
                with st.expander(f"⬜ {control_name}", expanded=False):
                    st.caption("This control is not included in this report.")


def render_comparisons(left_report_obj, right_report_obj) -> None:
    """Render the control comparisons for the selected reports.
    
    Args:
        left_report_obj: Generated VendorReport object for the left report
        right_report_obj: Generated VendorReport object for the right report
    """
    # Get unique control names from both reports
    left_control_names = {c.name for c in left_report_obj.controls}
    right_control_names = {c.name for c in right_report_obj.controls}
    all_control_names = sorted(left_control_names | right_control_names)
    
    # Loop through every control, compare status, and output a comparison indicator
    for control_name in all_control_names:
        left_control = next((c for c in left_report_obj.controls if c.name == control_name), None)
        right_control = next((c for c in right_report_obj.controls if c.name == control_name), None)
    
        if left_control is None:
            # Control only exists in right report
            with st.expander("➕ Added in Report 2"):
                st.write(f"**Status in Report 2:** {'✅ Pass' if right_control.status == 1 else '❌ Fail'}")
                if current_user_has_permission(Permission.VIEW_EVIDENCE):
                    st.write(f"**Evidence:** {right_control.evidence}")
                else:
                    st.caption("🔒 Evidence view is restricted to administrators only.")
        elif right_control is None:
            # Control only exists in left report
            with st.expander("➖ Removed from Report 2"):
                st.write(f"**Status in Report 1:** {'✅ Pass' if left_control.status == 1 else '❌ Fail'}")
                if current_user_has_permission(Permission.VIEW_EVIDENCE):
                    st.write(f"**Evidence:** {left_control.evidence}")
                else:
                    st.caption("🔒 Evidence view is restricted to administrators only.")
        else:
            # Control exists in both reports
            if left_control.status == PASS and right_control.status == PASS:
                with st.expander("↔️ Both Pass"):
                    st.write("This control passed in both reports.")

            elif left_control.status == FAIL and right_control.status == FAIL:
                with st.expander("↔️ Both Fail"):
                    st.write("This control failed in both reports.")

            elif left_control.status == PASS and right_control.status == FAIL:
                with st.expander("📉 Pass → Fail"):
                    st.write(f"**Report 1:** ✅ Pass")
                    if current_user_has_permission(Permission.VIEW_EVIDENCE):
                        st.caption(f"{left_control.evidence}")
                    else:
                        st.caption("🔒 Evidence restricted to admins")
                    st.write(f"**Report 2:** ❌ Fail")
                    if current_user_has_permission(Permission.VIEW_EVIDENCE):
                        st.caption(f"{right_control.evidence}")
                    else:
                        st.caption("🔒 Evidence restricted to admins")
                    
            elif left_control.status == FAIL and right_control.status == PASS:
                with st.expander("📈 Fail → Pass"):
                    st.write(f"**Report 1:** ❌ Fail")
                    if current_user_has_permission(Permission.VIEW_EVIDENCE):
                        st.caption(f"{left_control.evidence}")
                    else:
                        st.caption("🔒 Evidence restricted to admins")
                    st.write(f"**Report 2:** ✅ Pass")
                    if current_user_has_permission(Permission.VIEW_EVIDENCE):
                        st.caption(f"{right_control.evidence}")
                    else:
                        st.caption("🔒 Evidence restricted to admins")