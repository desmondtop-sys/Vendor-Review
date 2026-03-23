import streamlit as st

from backend.vendor_database import (
    get_vendor_documents_path,
    save_vendor_upload_metadata,
    load_vendor_upload_metadata,
    get_vendor_model_by_id
)
from backend.config_manager import get_client_documents
from backend.permissions import Permission
from frontend.auth_helpers import current_user_has_permission
from frontend.views.shared_components_view import render_logo, render_vertical_divider
from defs import Requirement


def render_client_upload_page() -> None:
    """Render the client-facing document upload page."""
    
    # Hide anchors over all elements
    st.markdown("""
    <style>
    [data-testid="stHeaderActionElements"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # For client users, use their assigned vendor ID from the database
    vendor_id = st.session_state.get("user_assigned_vendor_id")
    
    if not vendor_id:
        st.error("❌ Your account is not linked to a vendor. Please contact an administrator.")
        st.stop()
    
    # Get vendor information
    vendor = get_vendor_model_by_id(vendor_id)
    if not vendor:
        st.error("❌ Vendor not found. Please contact an administrator.")
        st.stop()
    
    # Header with logout button
    logo_col, title_col, logout_col = st.columns([0.07, 0.78, 0.15])

    with logo_col:
        render_logo()
    with title_col:
        st.title(f"📤 {vendor.name} - Document Uploader")
    with logout_col:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Check if user has upload permission
    if not current_user_has_permission(Permission.UPLOAD_DOCUMENTS):
        st.error("⛔ You do not have permission to upload documents.")
        st.stop()
    
    # Load existing upload metadata
    upload_metadata = load_vendor_upload_metadata(vendor_id)
    
    # Load required documents from config
    required_documents = get_client_documents()
    
    # Initialize per-document uploader IDs if not already done
    for doc_type in required_documents.keys():
        uploader_key = f"uploader_id_{doc_type.replace(' ', '_')}"
        if uploader_key not in st.session_state:
            st.session_state[uploader_key] = 0
    
    # Check if SOC 2 report has been uploaded
    soc2_provided = "SOC 2 Type II Report" in upload_metadata
    
    # Introduction
    intro_text = "<h3>Welcome to the Document Upload Portal</h3>"
    intro_text += "\n\nPlease upload the following documents for our security evaluation."
    intro_text += "\n- Documents marked with **🔴** are required"
    intro_text += "\n- Documents marked with **🟡** are optional"
    if soc2_provided:
        intro_text += "\n- Documents marked with **⚪** are made optional by your SOC 2 report submission"
    else:
        intro_text += "\n- Documents marked with **⚪** are required unless you upload a SOC 2 report"
    intro_text += "\n\n**Accepted file formats:** PDF, Excel (.xlsx, .xls), CSV"
    st.markdown(intro_text, unsafe_allow_html=True)
    
    st.markdown("---")
    
    render_uploader_modules(required_documents, vendor_id, upload_metadata, soc2_provided)
    
    st.markdown("---")
    
    # Summary section
    render_upload_summary(upload_metadata, required_documents, soc2_provided)

def render_uploader_modules(required_documents: dict, vendor_id: int, upload_metadata: dict, soc2_provided: bool) -> None:
    # Create two columns for document uploaders
    col1, spacer, col2 = st.columns([0.5,0.02,0.5])
    current_col = col1
    col_idx = 0

    with spacer:
        render_vertical_divider("240vh")
    
    # Create uploaders for each document type, alternating between columns
    for doc_type, doc_info in required_documents.items():
        requirement = doc_info.get("requirement", Requirement.REQUIRED.value)
        
        # If SOC 2 is provided, redundant documents become optional
        if requirement == Requirement.REDUNDANT_WITH_SOC2.value and soc2_provided:
            requirement = Requirement.OPTIONAL.value
        
        with current_col:
            render_document_uploader(
                doc_type=doc_type,
                description=doc_info["description"],
                requirement=requirement,
                vendor_id=vendor_id,
                upload_metadata=upload_metadata,
                soc2_provided=soc2_provided
            )
            
            st.divider()
        
        # Alternate columns
        col_idx += 1
        current_col = col2 if col_idx % 2 == 1 else col1



def render_document_uploader(
    doc_type: str, 
    description: str, 
    requirement: str, 
    vendor_id: int,
    upload_metadata: dict,
    soc2_provided: bool = False
) -> None:
    """Render an individual document uploader.
    
    Args:
        doc_type (str): The type/name of the document
        description (str): Description of what this document should contain
        requirement (str): The requirement status ("required", "optional", or "redundant_with_soc2")
        vendor_id (int): The vendor ID to save files to
        upload_metadata (dict): Current upload metadata
        soc2_provided (bool): Whether SOC 2 report has been uploaded
    """
    
    # Display document type and description
    if requirement == Requirement.REQUIRED.value:
        status_icon = "🔴"
    elif requirement == Requirement.OPTIONAL.value:
        status_icon = "🟡"
    elif requirement == Requirement.REDUNDANT_WITH_SOC2.value:
        if soc2_provided:
            status_icon = "⚪"
        else:
            status_icon = "⚪"
    else:
        status_icon = "🟡"
    
    st.markdown(f"<h4>{status_icon} {doc_type}</h4>", unsafe_allow_html=True)
    st.caption(f"{description}")
    
    # Show current upload status
    if doc_type in upload_metadata:
        current_file = upload_metadata[doc_type]
        st.success(f"✅ Uploaded: {current_file}")
    else:
        st.info("⏳ Not uploaded")
    
    # Get uploader ID for this document type
    uploader_key_name = f"uploader_id_{doc_type.replace(' ', '_')}"
    uploader_id = st.session_state.get(uploader_key_name, 0)
    
    # File uploader (accepts only one file)
    uploaded_file = st.file_uploader(
        f"Choose file for {doc_type}",
        type=["pdf", "xlsx", "xls", "csv"],
        accept_multiple_files=False,
        key=f"uploader_{doc_type.replace(' ', '_')}_{uploader_id}",
        label_visibility="collapsed"
    )
    
    # If a file was uploaded, save it
    if uploaded_file:
        save_document(
            uploaded_file=uploaded_file,
            doc_type=doc_type,
            vendor_id=vendor_id,
            upload_metadata=upload_metadata
        )
    
    # Display previously uploaded file as a download button
    if doc_type in upload_metadata:
        documents_path = get_vendor_documents_path(vendor_id)
        file_name = upload_metadata[doc_type]
        file_path = documents_path / file_name
        
        if file_path.exists():
            dl_col, del_col = st.columns([0.85, 0.15])
            
            with dl_col:
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"📥 Download: {file_name}",
                        data=f,
                        file_name=file_name,
                        mime="application/octet-stream",
                        use_container_width=True,
                        key=f"dl_{doc_type.replace(' ', '_')}_{vendor_id}"
                    )
            
            with del_col:

                # This button deliberately does not delete the file from disk, only clears the metadata so it no longer shows as uploaded for the client. 
                # This allows us better control over our records.
                if st.button(
                    "🗑️",
                    key=f"del_{doc_type.replace(' ', '_')}_{vendor_id}",
                    help="Clear upload",
                    use_container_width=True
                ):
                    clear_document_metadata(doc_type, vendor_id, upload_metadata)
    else:
        # Show disabled buttons when no document is uploaded
        dl_col, del_col = st.columns([0.85, 0.15])
        
        with dl_col:
            st.button(
                "📥 No document uploaded",
                disabled=True,
                use_container_width=True,
                key=f"dl_disabled_{doc_type.replace(' ', '_')}_{vendor_id}"
            )
        
        with del_col:
            st.button(
                "🗑️",
                disabled=True,
                use_container_width=True,
                key=f"del_disabled_{doc_type.replace(' ', '_')}_{vendor_id}",
                help="No document to delete"
            )


def save_document(
    uploaded_file,
    doc_type: str,
    vendor_id: int,
    upload_metadata: dict
) -> None:
    """Save an uploaded document to the vendor's documents folder.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        doc_type (str): The type/name of the document
        vendor_id (int): The vendor ID to save files to
        upload_metadata (dict): Current upload metadata
    """
    
    # Get vendor documents path
    documents_path = get_vendor_documents_path(vendor_id)
    documents_path.mkdir(parents=True, exist_ok=True)
    
    # If there's an existing file for this document type, delete it first
    if doc_type in upload_metadata:
        old_filename = upload_metadata[doc_type]
        old_path = documents_path / old_filename
        if old_path.exists():
            old_path.unlink()
    
    # Save the new file
    dest_path = documents_path / uploaded_file.name
    dest_path.write_bytes(uploaded_file.getbuffer())
    
    # Update metadata
    upload_metadata[doc_type] = uploaded_file.name
    save_vendor_upload_metadata(vendor_id, upload_metadata)
    
    st.success(f"✅ Successfully uploaded: {uploaded_file.name}")
    
    # Increment uploader ID for this document type to force a fresh uploader widget
    uploader_key = f"uploader_id_{doc_type.replace(' ', '_')}"
    st.session_state[uploader_key] = st.session_state.get(uploader_key, 0) + 1
    
    st.rerun()


def clear_document_metadata(doc_type: str, vendor_id: int, upload_metadata: dict) -> None:
    """Clear metadata for an uploaded document (file remains on disk).
    
    Args:
        doc_type (str): The type/name of the document
        vendor_id (int): The vendor ID
        upload_metadata (dict): Current upload metadata
    """
    
    # Remove from metadata
    if doc_type in upload_metadata:
        del upload_metadata[doc_type]
        save_vendor_upload_metadata(vendor_id, upload_metadata)
    
    st.success(f"✅ Cleared metadata for {doc_type}")
    st.rerun()


def render_upload_summary(upload_metadata: dict, required_documents: dict, soc2_provided: bool = False) -> None:
    """Render a summary of upload progress.
    
    Args:
        upload_metadata (dict): Current upload metadata
        required_documents (dict): Required documents configuration from config file
        soc2_provided (bool): Whether SOC 2 report has been uploaded
    """
    
    st.markdown("### 📊 Upload Summary")
    
    # Calculate progress based on requirement status
    required_docs = {k: v for k, v in required_documents.items() if v.get("requirement") == Requirement.REQUIRED.value}
    optional_docs = {k: v for k, v in required_documents.items() if v.get("requirement") == Requirement.OPTIONAL.value}
    redundant_docs = {k: v for k, v in required_documents.items() if v.get("requirement") == Requirement.REDUNDANT_WITH_SOC2.value}
    
    # Categorize docs based on SOC 2 status
    if soc2_provided:
        # If SOC 2 is provided, redundant docs become optional
        required_docs_to_show = {k: v for k, v in required_docs.items()}
        optional_docs_to_show = {**optional_docs, **redundant_docs}
    else:
        # If SOC 2 is NOT provided, redundant docs count as required
        required_docs_to_show = {**required_docs, **redundant_docs}
        optional_docs_to_show = {k: v for k, v in optional_docs.items()}
    
    required_uploaded = sum(1 for doc in required_docs_to_show.keys() if doc in upload_metadata)
    optional_uploaded = sum(1 for doc in optional_docs_to_show.keys() if doc in upload_metadata)
    
    total_required = len(required_docs_to_show)
    total_optional = len(optional_docs_to_show)
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Required Documents",
            f"{required_uploaded} / {total_required}",
            delta=f"{(required_uploaded/total_required*100):.0f}% complete" if total_required > 0 else "N/A"
        )
    
    with col2:
        st.metric(
            "Optional Documents",
            f"{optional_uploaded} / {total_optional}",
            delta=f"{(optional_uploaded/total_optional*100):.0f}% complete" if total_optional > 0 else "N/A"
        )
    
    with col3:
        total_uploaded = len(upload_metadata)
        total_docs = len(required_docs_to_show) + len(optional_docs_to_show)
        st.metric(
            "Total Progress",
            f"{total_uploaded} / {total_docs}",
            delta=f"{(total_uploaded/total_docs*100):.0f}% complete"
        )
    
    # Completion status
    if required_uploaded == total_required:
        st.success("🎉 All required documents have been uploaded! Thank you for your submission.")
        st.info("💡 You can still upload optional documents to provide additional context for the evaluation.")
    else:
        missing = total_required - required_uploaded
        st.warning(f"⚠️ {missing} required document{'s' if missing != 1 else ''} still needed.")
    
    # List missing required documents
    if required_uploaded < total_required:
        st.markdown("#### Missing Required Documents:")
        for doc_type in required_docs_to_show.keys():
            if doc_type not in upload_metadata:
                st.markdown(f"🔴 {doc_type}")