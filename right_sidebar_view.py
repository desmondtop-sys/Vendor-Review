import streamlit as st

from backend.vendor_database import create_vendor, get_vendor_documents_path
from backend.permissions import Permission

from frontend.styles import get_styles
from frontend.state_manager import reset_states, reset_sandbox
from frontend.views.shared_components_view import render_documents, render_generate_report_button, render_pdf_downloader
from frontend.auth_helpers import current_user_has_permission


def render_right_sidebar() -> None:
    """Render the full right sidebar including upload, documents, and PDF tools."""

    st.markdown(get_styles("right_sidebar"), unsafe_allow_html=True)

    render_uploader()
    
    if st.session_state.current_tab == "Assets":
        return

    st.divider()

    render_documents(0.8, 0.2)

    render_generate_report_button()

    st.divider()

    render_pdf_downloader()


def render_uploader() -> None:
    """Render document uploader and persist uploaded files to the vendor's documents folder."""

    st.subheader("📤 Upload Documents")
    uploaded_files = st.file_uploader(
        "Add PDFs and Spreadsheets to this evaluation", 
        type=["pdf", "xlsx", "xls", "csv"], 
        accept_multiple_files=True, 
        key=f"uploader_{st.session_state.uploader_id}",
        disabled=not current_user_has_permission(Permission.UPLOAD_DOCUMENTS),
    )

    if uploaded_files:
        vendor_id = st.session_state.get("active_vendor_id")

        # If no vendor exists, create a default vendor
        if not vendor_id:
            vendor_id = create_vendor("New Vendor")
            st.session_state.active_vendor_id = vendor_id

        # Get vendor documents path
        documents_path = get_vendor_documents_path(vendor_id)
        documents_path.mkdir(parents=True, exist_ok=True)

        # Process every file in the upload queue - save directly to vendor documents
        for f in uploaded_files:
            dest_path = documents_path / f.name
            dest_path.write_bytes(f.getbuffer())
        
        # Reset uploader widget and refresh the UI to show new files
        reset_states()
        reset_sandbox()
        st.rerun()