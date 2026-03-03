"""Shared rendering components used across multiple pages.

This module provides reusable render functions for common UI patterns
that appear in different views throughout the application.
"""
from pathlib import Path

import streamlit as st

from backend.models import Report, Vendor
from backend.IO_engine import generate_pdf_report
from backend.report_utils import calculate_score
from backend.config_manager import get_threshold_settings
from backend.vendor_database import get_vendor_documents_path, delete_vendor, set_vendor_nda_signed

from frontend.state_manager import handle_vendor_switch, reset_states
from frontend.utils import get_badge_styles


def render_documents(doc_width: float, del_width: float) -> None:
    """Render source document list, deletion controls, and analysis trigger button."""

    # Only admins can view/manage documents
    if not st.session_state.get("is_admin", False):
        return

    vendor_id = st.session_state.get("active_vendor_id")
    
    if not vendor_id:
        return
    
    # Validate vendor still exists
    from backend.vendor_database import get_vendor_model_by_id
    vendor = get_vendor_model_by_id(vendor_id)
    if vendor is None:
        st.error("⚠️ This vendor no longer exists. It may have been deleted.")
        return

    nda_signed = vendor.nda_signed
        
    st.subheader("📄 Source Documents", anchor=False)

    # Get vendor documents path
    documents_path = get_vendor_documents_path(vendor_id)
    
    if not documents_path.exists():
        documents_path.mkdir(parents=True, exist_ok=True)
    
    # List all files in the vendor's documents folder
    document_files = sorted([f.name for f in documents_path.iterdir() if f.is_file()])
    
    if not document_files:
        st.info("No documents uploaded yet. Use the uploader to add files.")

    visible_docs = document_files
    
    # Limit sidebar list to avoid pushing buttons too far down
    if st.session_state.current_tab != "Assets":
        max_docs = 5
        visible_docs = document_files[:max_docs]

        if len(document_files) > max_docs:
            st.caption(f"Full list on Assets page ({len(document_files)} total)")

    # List files as stylized blocks
    for name in visible_docs:

        # Create a split for the View button and the Delete button
        btn_col, del_col = st.columns([doc_width, del_width])

        # Construct file path in vendor documents folder
        file_path = documents_path / name
        
        if file_path.exists():
            with btn_col:
                if nda_signed:
                    st.markdown(f"📄 {name}")
                else:
                    with open(file_path, "rb") as f:
                        # Download button acts as an "Open" trigger for PDFs
                        st.download_button(
                            label=f"{name}",
                            data=f,
                            file_name=name,
                            mime="application/pdf",
                            width='stretch',
                            key=f"dl_{name}_{vendor_id}"
                        )

            with del_col:
                # Use a small button for deletion of files
                if st.button("🗑️", key=f"del_{name}_{vendor_id}", help=f"Delete {name}"):
                    # Delete the file from disk
                    file_path.unlink()
                    st.rerun()

    if nda_signed and document_files:
        st.caption("🔒 NDA is signed for this vendor. Source document downloads are disabled to prevent accidental disclosure.")

    st.divider()


def render_generate_report_button() -> None:
    """Render the 'Generate Report' button to trigger AI analysis of uploaded documents."""

    # Only admins can generate reports
    if not st.session_state.get("is_admin", False):
        return
    
    # Show if the vendor has files
    vendor_id = st.session_state.get("active_vendor_id")
    
    # Validate vendor still exists
    from backend.vendor_database import get_vendor_model_by_id
    if not vendor_id or get_vendor_model_by_id(vendor_id) is None:
        return
        
    documents_path = get_vendor_documents_path(vendor_id) if vendor_id else None
    
    document_files = sorted([f.name for f in documents_path.iterdir() if f.is_file()]) if documents_path else []

    if not document_files:
        return
    
    if st.button("🚀 Generate Report", type="primary", width='stretch'):
        st.session_state.analysis_in_progress = True
        st.rerun()


def render_pdf_downloader() -> None:
    """Render controls to generate and download a PDF summary for the active report."""
    
    vendor_id = st.session_state.get("active_vendor_id")

    # Validate vendor still exists
    from backend.vendor_database import get_vendor_model_by_id
    if vendor_id and get_vendor_model_by_id(vendor_id) is None:
        st.error("⚠️ This vendor no longer exists. It may have been deleted.")
        return

    # Check if there's an active report to generate a PDF from
    if vendor_id and "active_report" in st.session_state:
        report = st.session_state.active_report

        st.subheader("📥 Download Report", anchor=False)

        if not report:
            st.info("Select a report to enable PDF download.")
            st.divider()
            return

        # Initialize a PDF holder
        if "live_pdf_data" not in st.session_state:
            st.session_state.live_pdf_data = None

        # Button updates the data whenever you want a fresh version
        if st.button("🔄 Sync & Prepare PDF", width='stretch', key="sync_pdf_btn"):
            with st.spinner("Updating report data..."):
                # This is where we update the data value "on the fly"
                st.session_state.live_pdf_data = generate_pdf_report()
            st.success("PDF ready to download!")

        # This button is always looking at st.session_state.live_pdf_data
        if st.session_state.live_pdf_data:
        
            # Wrap in a container so we can target it for styles
            with st.container(key="report_download_container"):
                st.download_button(
                    label="📥 Download Prepared PDF",
                    data=st.session_state.live_pdf_data,
                    file_name=f"Audit_{report.vendor_name}.pdf",
                    mime="application/pdf",
                    width='stretch',
                    type="primary"
                )
    
        st.divider()


def render_security_score(report: Report) -> None:
    """Render the styled security score card for the current report view.

    Computes score and threshold status, then outputs a color-coded Streamlit
    markdown block showing points, percentage, and pass/fail label.
    """

    score, possible, must_pass_failed = calculate_score(report)

    # Determine the color hex codes
    percentage = (score / possible) * 100 if possible > 0 else 0
    # Use cached thresholds from session (loaded at login)
    thresholds = st.session_state.get("cached_threshold_settings", get_threshold_settings())
    pass_limit = thresholds["pass_threshold"]
    fail_limit = thresholds["fail_threshold"]
    
    if must_pass_failed:
        bg_color, text_color = "#f8d7da", "#721c24"  # Light Red
        result = "CRITICAL FAILURE"
    else:
        if percentage >= pass_limit:
            bg_color, text_color = "#d4edda", "#155724"  # Light Green
            result = "PASSED"
        elif percentage >= fail_limit:
            bg_color, text_color = "#fff3cd", "#856404"  # Light Orange/Yellow
            result = "NEEDS REVIEW"
        else:
            bg_color, text_color = "#f8d7da", "#721c24"  # Light Red
            result = "FAILED"
    
    # Use Markdown with HTML to create the highlighted box
    st.markdown(
        f"""
        <div style="
            background-color: {bg_color};
            color: {text_color};
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid {text_color};
        ">
            <span style="font-size: 13px; font-weight: bold; display: block;">SECURITY SCORE - {result}</span>
            <span style="font-size: 36px; font-weight: 800;">{score} / {possible} ({percentage:.2f}%)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_oneline_security_score(report: Report) -> None:
    """Render a compact security score badge for use in tight spaces."""

    if not report:
        st.markdown(
            f"""
            <div style="
                background-color: #343541;
                padding: 8px;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                color: #999;
            ">
                No Report Available
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    score, possible, must_pass_failed = calculate_score(report)
    status, status_color, text_color = get_badge_styles(score, possible, must_pass_failed)

    st.markdown(
                f"""
                <div style="
                    background-color: {status_color};
                    padding: 8px;
                    border-radius: 5px;
                    text-align: center;
                    font-weight: bold;
                    color: {text_color};
                ">
                    {score}/{possible} - {status}
                </div>
                """,
                unsafe_allow_html=True,
            )


def vertical_divider(height: str = "20vh") -> None:
    """Render a vertical divider of specified height.

    Args:
        height (str, optional): CSS height value for the divider. Defaults to "20px".
    """
    st.markdown(
        f'<div class="app-shell-divider" style="height: {height};"></div>',
        unsafe_allow_html=True
    )


def render_delete_vendor_button(vendor: Vendor | None = None) -> None:
    """Render a delete button for a vendor with confirmation.
    
    Uses the active_vendor_id from session state if vendor is not provided.
    
    Args:
        vendor (Vendor, optional): Vendor model containing id and name.
                                If None, uses active_vendor_id from session state.
    """
    if not st.session_state.get("is_admin", False):
        return

    if vendor is None:
        return
    
    # Use a unique confirmation phase key per vendor
    vendor_id = vendor.id
    confirm_key = f"delete_confirm_phase_{vendor_id}"
    confirm_page_key = f"delete_confirm_page_{vendor_id}"
    current_page = st.session_state.get("current_page")

    # Reset confirmation if the user navigated away
    if st.session_state.get(confirm_key, False):
        if st.session_state.get(confirm_page_key) != current_page:
            st.session_state[confirm_key] = False
            st.session_state.pop(confirm_page_key, None)
    
    # If we aren't confirming, show the initial delete button
    if not st.session_state.get(confirm_key, False):
        if st.button("🗑️ Delete This Vendor", type="primary", key=f"delete_btn_{vendor_id}", width='stretch'):
            st.session_state[confirm_key] = True
            st.session_state[confirm_page_key] = current_page
            st.rerun()  # Force rerun to show the confirmation UI
                
    # If we ARE confirming, show the "Are you sure?" UI
    else:
        st.warning("⚠️ This action cannot be undone. Are you sure?")
                    
        c1, c2 = st.columns(2)
                    
        with c1:
            if st.button("❌ No", key=f"cancel_delete_{vendor_id}", width='stretch'):
                # Reset the phase if they change their mind
                st.session_state[confirm_key] = False
                st.session_state.pop(confirm_page_key, None)
                st.rerun()

        with c2:
            if st.button("✅ Yes", type="primary", key=f"confirm_delete_{vendor_id}", width='stretch'):
                # Execute deletion logic
                    
                delete_vendor(vendor_id)
                    
                # Clear states if this is the active vendor
                if st.session_state.get("active_vendor_id") == vendor_id:
                    st.session_state.active_vendor_id = None
                    st.session_state.active_report = None
                    reset_states()
                    
                # Reset confirmation phase
                st.session_state[confirm_key] = False
                st.session_state.pop(confirm_page_key, None)
                    
                st.toast("Vendor Deleted")
                st.rerun()


def render_nda_toggle_button(vendor: Vendor | None = None) -> None:
    """Render a button to toggle NDA signed status for a vendor.

    Args:
        vendor (Vendor | None): Vendor model. If None, no button is rendered.
    """
    if not st.session_state.get("is_admin", False):
        return

    if vendor is None or vendor.id is None:
        return

    if vendor.nda_signed:
        button_label = "🔓 Mark NDA Unsigned"
        button_help = "Allow source document downloads for this vendor"
    else:
        button_label = "🔒 Mark NDA Signed"
        button_help = "Disable source document downloads for this vendor"

    if st.button(button_label, type="secondary", width='stretch', key=f"nda_toggle_{vendor.id}", help=button_help):
        set_vendor_nda_signed(vendor.id, not vendor.nda_signed)
        st.toast(f"NDA status updated for {vendor.name}.")
        st.rerun()

def render_vendor_selector_button(vendor: Vendor, key_prefix: str = "") -> None:
    # Determine button type: 'primary' for the selected one, 'secondary' for others

    disabled = st.session_state.get("analysis_in_progress", False)

    # Determine highlight status based on current vendor
    active_vendor_id = st.session_state.get("active_vendor_id")

    if vendor.id == active_vendor_id and st.session_state.current_page == "Dashboard":
        btn_type = "primary" 
    else:
        btn_type = "secondary"

    # Apply the style and check for clicks
    if st.button(
        f"🏢 {vendor.name}", 
        key=f"{key_prefix}view_vendor_{vendor.id}", 
        width='stretch',
        type=btn_type,
        disabled=disabled
    ):
        # Switch to vendor (which loads latest report)
        handle_vendor_switch(vendor.id)
        
        st.rerun()

def render_logo() -> None:
    """Render the Hydro Ottawa logo."""

    logo_path = Path(__file__).resolve().parents[2] / "Resources" / "hydro_ottawa_logo.png"
    if logo_path.exists():

        st.image(str(logo_path), width='stretch')