import streamlit as st

from backend.bitsight_client import get_company_rating_by_name
from backend.vendor_database import get_vendor_model_by_id, update_vendor_bitsight

from frontend.styles import get_styles
from frontend.views.shared_components_view import (
    render_documents,
    render_generate_report_button,
    render_pdf_downloader,
)


def render_assets_page() -> None:
    """Render the Assets page with uploads, records, and report generation."""

    st.markdown(get_styles("assets"), unsafe_allow_html=True)

    render_bitsight_information()

    render_documents(0.95, 0.05)

    render_generate_report_button()

    render_pdf_downloader()


def render_bitsight_information() -> None:
    """Render Bitsight score controls."""

    vendor_id = st.session_state.get("active_vendor_id")
    if not vendor_id:
        return

    vendor = get_vendor_model_by_id(vendor_id)
    if not vendor:
        return
    
    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        st.subheader("Bitsight", anchor=False)

        current_score = vendor.bitsight_rating
        rating_date = vendor.bitsight_rating_date

        if rating_date:
            st.caption(f"Last API rating date: {rating_date}")
        else:
            st.caption("No API rating date stored.")

    with col2:
        # Reset button
        if st.button("Reset Bitsight Information", type="secondary", help="Clear all Bitsight data from database"):
            update_vendor_bitsight(
                vendor_id,
                company_guid=None,
                company_name=None,
                rating=None,
                rating_date=None,
            )
            st.success("Bitsight information has been reset.")
            st.rerun()

    col1, col2 = st.columns([0.8, 0.2])

    with col1:
        company_name = vendor.bitsight_company_name
        company_guid = vendor.bitsight_company_guid
        if company_name or company_guid or rating_date:
            st.markdown(f"GUID: {company_guid or 'Unknown'}")

    with col2:
        render_bitsight_score()

    score_value = int(current_score) if current_score is not None else 0
    new_score = st.number_input(
        "Bitsight Score",
        min_value=0,
        max_value=1000,
        value=score_value,
        step=1,
    )

    save_col, fetch_col = st.columns(2, gap="medium")

    with save_col:
        button_type = "tertiary" if new_score != score_value else "secondary"

        if st.button("Save Manual Score", type=button_type, width='stretch'):
            update_vendor_bitsight(
                vendor_id,
                company_guid=vendor.bitsight_company_guid,
                company_name=vendor.bitsight_company_name,
                rating=int(new_score),
                rating_date=vendor.bitsight_rating_date,
            )
            st.success("Bitsight score updated.")
            st.rerun()

    with fetch_col:
        if st.button("Fetch from Bitsight API", type="primary", width='stretch'):
            with st.spinner("Fetching Bitsight rating..."):
                bitsight_data = get_company_rating_by_name(vendor.name)
            if bitsight_data:
                update_vendor_bitsight(
                    vendor_id,
                    company_guid=bitsight_data.get("company_guid"),
                    company_name=bitsight_data.get("company_name"),
                    rating=bitsight_data.get("rating"),
                    rating_date=bitsight_data.get("rating_date"),
                )
                st.success("Bitsight rating updated from API.")
                st.info(
                    f"API data: {bitsight_data.get('company_name') or 'Unknown'} | "
                    f"{bitsight_data.get('company_guid') or 'Unknown'} | "
                    f"{bitsight_data.get('rating_date') or 'Unknown'}"
                )
                st.rerun()
            else:
                st.error(f"No matching company found in Bitsight API for name '{vendor.name}'.")
                update_vendor_bitsight(
                    vendor_id,
                    company_guid=None,
                    company_name=None,
                    rating=None,
                    rating_date=None,
                )

    st.divider()


def render_bitsight_score() -> None:
    """Render the Bitsight score badge on the report view."""

    vendor_id = st.session_state.get("active_vendor_id")
    if not vendor_id:
        return
    vendor = get_vendor_model_by_id(vendor_id)
    if not vendor:
        return

    current_score = vendor.bitsight_rating

    possible_score = 900
    score_value = int(current_score) if current_score is not None else 0
    ratio = score_value / possible_score if possible_score else 0
    if ratio >= 0.75:
        badge_bg, badge_text, badge_border = "#d4edda", "#155724", "#155724"
    elif ratio >= 0.6:
        badge_bg, badge_text, badge_border = "#fff3cd", "#856404", "#856404"
    else:
        badge_bg, badge_text, badge_border = "#f8d7da", "#721c24", "#721c24"

    st.markdown(
        f"""
        <div style="
            background-color: {badge_bg};
            color: {badge_text};
            padding: 8px 12px;
            border-radius: 999px;
            display: inline-block;
            font-weight: 700;
            border: 1px solid {badge_border};
            margin-bottom: 8px;
        ">
            Bitsight Score: {score_value} / {possible_score}
        </div>
        """,
        unsafe_allow_html=True
    )
