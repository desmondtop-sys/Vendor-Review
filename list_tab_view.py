import streamlit as st

from backend.models import Vendor
from backend.vendor_database import create_vendor, generate_vendor_report_from_db, get_active_report_for_vendor, get_all_vendor_models, get_latest_report_for_vendor, get_report_by_id

from frontend.styles import get_styles
from frontend.views.shared_components_view import render_delete_vendor_button, render_oneline_security_score, render_vendor_selector_button


def render_vendor_list_tab() -> None:
    """Render the Vendors page with vendor list and management controls."""

    vendors = get_all_vendor_models()

    for vendor in vendors:
        vendor_col, info_col, delete_col = st.columns([0.2, 0.6, 0.2])

        with vendor_col:
            render_vendor_selector_button(vendor, key_prefix="main_")

        with info_col:
            render_vendor_information(vendor)

        st.divider()
        
        with delete_col:
            render_delete_vendor_button(vendor)

def render_vendor_information(vendor: Vendor) -> None:
    """Render information about a vendor."""

    identification_col, security_score_col = st.columns([0.5, 0.5])

    with identification_col:
        st.markdown(f"**{vendor.name}**")
        st.markdown(f"ID: {vendor.id}")

    with security_score_col:
        # Get the active report for this vendor
        vendor_id = vendor.id
        report_id = get_active_report_for_vendor(vendor_id)
        
        # Fall back to latest report
        if not report_id:
            report_row = get_latest_report_for_vendor(vendor_id)
            report_id = report_row['id'] if report_row else None
        
        # Render the score
        report_obj = None
        if report_id:
            report_row = get_report_by_id(report_id)
            if report_row:
                report_obj = generate_vendor_report_from_db(report_row)
        render_oneline_security_score(report_obj)