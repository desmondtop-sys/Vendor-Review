"""Report history viewer for tracking vendor assessment versions over time."""

import streamlit as st

from backend.vendor_database import (
    delete_report,
    get_all_vendor_reports,
    generate_vendor_report_from_db,
    set_active_report_for_vendor,
    get_active_report_for_vendor,
    get_report_by_id,
    get_vendor_model_by_id
)
from backend.report_utils import calculate_score
from backend.permissions import Permission

from frontend.auth_helpers import current_user_has_permission
from frontend.state_manager import reset_sandbox
from frontend.views.shared_components_view import render_oneline_security_score


def render_report_history() -> None:
    """Render the report history timeline for the active vendor."""


    if not st.session_state.get("active_vendor_id"):
        st.info("Select a vendor to view its report history.")
        return

    vendor_id = st.session_state.active_vendor_id
    
    # Validate vendor still exists
    if get_vendor_model_by_id(vendor_id) is None:
        st.error("⚠️ This vendor no longer exists. It may have been deleted.")
        return
    
    reports = get_all_vendor_reports(vendor_id)

    if not reports:
        st.info("No reports yet for this vendor. Upload documents and Generate Report to create one.")
        return

    title_col, runtime_col, score_col, spacer = st.columns([0.45, 0.15, 0.25, 0.15])
    with title_col:
        st.subheader("📜 Report History")
    with runtime_col:
        st.subheader("⏱️ Runtime")
    with score_col:
        st.subheader("📈 Security Score")
    st.divider()

    for report in reports:
        report_obj = generate_vendor_report_from_db(report)
        
        # Check if this is the currently active report
        is_active = (st.session_state.get("active_report") and st.session_state.active_report.id == report['id'])        

        col1, col2, col3, col4, col5, col6 = st.columns([0.05, 0.40, 0.15, 0.25, 0.10, 0.05])

        # Print run number
        with col1:
            st.markdown(f"**v{report['run_number']}**")

        # Print timestamp and summary snippet
        with col2:
            timestamp = report["timestamp"][:10] if report["timestamp"] else "Unknown"
            st.markdown(f"_{timestamp}_ • {report['summary'][:110]}")

        with col3:
            # Show report runtime if available
            if report_obj.runtime is not None:
                st.markdown(f"⏱️ {report_obj.runtime:.1f}s")
            else:
                st.markdown("⏱️ Unknown")

        # Calculate and show security score
        with col4:
            render_oneline_security_score(report_obj)

        # Active report selection button
        with col5:
            # Set styles for active vs inactive reports
            button_label = "Active" if is_active else "Set as Active"
            button_type = "primary" if is_active else "secondary"
            
            if st.button(
                button_label,
                key=f"report_v{report['run_number']}_{vendor_id}",
                width='stretch',
                type=button_type,
                disabled=not current_user_has_permission(Permission.SELECT_REPORTS),
            ):
                set_active_report_for_vendor(vendor_id, report['id'])
                st.session_state.active_report = report_obj
                st.rerun()

        # Delete report button
        with col6:

            if st.button(
                "🗑️",
                key=f"delete_v{report['run_number']}_{vendor_id}",
                width='stretch',
                type="secondary",
                disabled=not current_user_has_permission(Permission.DELETE_REPORTS),
            ):
                delete_report(vendor_id, report['id'])
                
                # Clear simulation state to prevent errors with deleted report data
                reset_sandbox()
                
                # Reload the active report (database function already set the new active one)
                new_active_report_id = get_active_report_for_vendor(vendor_id)
                if new_active_report_id:
                    report_row = get_report_by_id(new_active_report_id)
                    st.session_state.active_report = generate_vendor_report_from_db(report_row)
                else:
                    st.session_state.active_report = None
                    
                st.rerun()
        
        st.divider()
