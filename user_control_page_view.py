import streamlit as st

from backend.user_database import delete_user, get_all_users, update_user_role, update_user_assigned_vendor, create_user
from backend.vendor_database import get_all_vendors
from backend.permissions import ROLE_PERMISSIONS
from frontend.styles import get_styles

def render_user_control_page():
    """Renders the User Control page in the Streamlit app."""

    st.markdown(get_styles("user_control_page"), unsafe_allow_html=True)

    title_col, search_col, new_user_col = st.columns([0.2, 0.6, 0.2])

    with title_col:
        st.title("User Control")
    with search_col:
        render_search_bar()
    with new_user_col:
        st.markdown("<div style='font-size: 17px;'>&nbsp;</div>", unsafe_allow_html=True)   # Spacer to vertically align the button with the title
        if st.button("➕ New User", width='stretch', type="primary"):
            st.session_state.show_create_user_modal = True
    
    st.divider()
    
    # Show modal if triggered
    if st.session_state.get("show_create_user_modal", False):
        render_create_user_modal()
    else:

        users = get_all_users()
        
        # Create vendor ID to name mapping
        vendors = get_all_vendors()
        vendor_map = {v['id']: v['name'] for v in vendors}
        
        
        # Filter by selected roles
        selected_roles = st.session_state.get("selected_roles", set())
        
        if selected_roles:
            users = [ user for user in users if user.role.value in selected_roles ]

        # Filter by search query
        search_query = st.session_state.get("user_search", "")

        if search_query:
            users = [
                user for user in users
                if (
                    search_query.lower() in user.username.lower()
                    or search_query.lower() in user.email.lower()
                    or (user.full_name and search_query.lower() in user.full_name.lower())
                    or (user.assigned_vendor_id and search_query.lower() in vendor_map.get(user.assigned_vendor_id, "").lower())
                )
            ]

        if not users:
            st.info("No users found. Try adjusting your search criteria.")

        for user in users:

            col1, col2, col3 = st.columns([0.5, 0.5, 0.5])

            with col1:
                print_user_info(user)
                render_delete_user_button(user)

            with col2:
                render_role(user)
                render_permissions(user)

            with col3:
                render_link_user_to_vendor(user)
        
            st.divider()

def render_search_bar():
    # Search bar
    search_query = st.text_input("🔍 Search users", placeholder="Search by username, email, name, or vendor...", key="user_search")
        
    # Role filter buttons
    roles = list(ROLE_PERMISSIONS.keys())
        
    # Initialize selected roles in session state (default to empty - no filters active)
    if "selected_roles" not in st.session_state:
        st.session_state.selected_roles = set()
        
    role_cols = st.columns(len(roles))
    for idx, role in enumerate(roles):
        with role_cols[idx]:
            is_selected = role.value in st.session_state.selected_roles
            if st.button(
                role.value.upper(),
                key=f"role_filter_{role.value}",
                type="primary" if is_selected else "secondary",
                width='stretch'
            ):
                if is_selected:
                    st.session_state.selected_roles.discard(role.value)
                else:
                    st.session_state.selected_roles.add(role.value)
                st.rerun()


def print_user_info(user):
    """Prints a single user's information in a formatted way in a bordered container."""
    
    # Render all content as markdown inside the bordered container
    user_info_html = f"""
    <div class='user-info-container'>
        <p><strong>Username:</strong> {user.username}</p>
        <p><strong>Email:</strong> {user.email}</p>
        <p><strong>Full Name:</strong> {user.full_name}</p>
    </div>
    """
    st.markdown(user_info_html, unsafe_allow_html=True)

def render_delete_user_button(user):
    """Display delete user button with multi-step verification."""
    
    deletion_key = f"delete_state_{user.id}"
    
    # Initialize deletion state if not present
    if deletion_key not in st.session_state:
        st.session_state[deletion_key] = "initial"
    
    state = st.session_state[deletion_key]
    
    # Step 1: Initial state - show delete button
    if state == "initial":
        if st.button(f"🗑️ Delete User", key=f"delete_btn_{user.id}", type="secondary"):
            st.session_state[deletion_key] = "confirm_step"
            st.rerun()
    
    # Step 2: Confirmation - require typing username
    elif state == "confirm_step":
        
        typed_username = st.text_input(
            f"Type the username **{user.username}** to confirm deletion:",
            key=f"username_confirm_{user.id}",
            placeholder=user.username,
        )
        
        col1, col2 = st.columns([0.5, 0.5])
        
        with col1:
            if st.button("Cancel", key=f"cancel_final_{user.id}", width='stretch', type="secondary"):
                st.session_state[deletion_key] = "initial"
                st.rerun()
        
        with col2:
            # Only enable delete button if username matches
            delete_enabled = typed_username == user.username
            if st.button(
                "⚠️ Delete Permanently",
                key=f"delete_final_{user.id}",
                type="secondary",
                disabled=not delete_enabled,
                width='stretch',
            ):
                # Perform deletion
                if delete_user(user.id):
                    st.success(f"✅ User {user.username} has been deleted.")
                    st.session_state[deletion_key] = "deleted"
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete user {user.username}")
                    st.session_state[deletion_key] = "initial"
    
    # Step 4: User deleted
    elif state == "deleted":
        st.info("User has been successfully deleted.")

def render_role(user):
    """Render the role selection dropdown for a user."""
    roles = list(ROLE_PERMISSIONS.keys())
    
    role = st.selectbox(
        "Role", 
        options=roles,
        key=f"role_select_{user.id}",
        index=roles.index(user.role),
        format_func=lambda role: role.value.upper(),
    )

    if role != user.role:
        update_user_role(user.id, role)
        st.success(f"User role updated to {role.value.upper()}")

def render_permissions(user):
    # Get permissions for this user's role
    permissions = ROLE_PERMISSIONS.get(user.role, [])
        
    with st.expander(f"📋 Permissions ({len(permissions)})"):
        if permissions:
            for permission in permissions:
                st.write(f"✅ {permission.value}")
        else:
            st.write("No permissions assigned")

def render_link_user_to_vendor(user):

    vendors = get_all_vendors()
    
    # Convert vendors to list of dicts for display
    vendor_list = [{**dict(v)} for v in vendors]
    vendor_ids = [None] + [v['id'] for v in vendor_list]
    vendor_names = ["No Vendor Assigned"] + [v['name'] for v in vendor_list]
    
    current_vendor = user.assigned_vendor_id
    current_index = vendor_ids.index(current_vendor) if current_vendor in vendor_ids else 0

    selected_index = st.selectbox(
        "Linked Vendor", 
        options=range(len(vendor_names)),
        key=f"vendor_select_{user.id}",
        index=current_index,
        format_func=lambda idx: vendor_names[idx],
    )
    
    if selected_index and selected_index > 0:
        selected_vendor_id = vendor_ids[selected_index]
    else:
        selected_vendor_id = None

    if selected_vendor_id != current_vendor:
        update_user_assigned_vendor(user.id, selected_vendor_id)
        st.success(f"User linked to vendor: {vendor_names[selected_index]}")


def render_create_user_modal():
    """Render the create user modal form."""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='background-color: #0e1117; padding: 15px; border-radius: 5px; border: 1px solid #31333d; margin-top: 50px;'>
        <h2>Create New User</h2>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", key="new_user_username", placeholder="e.g., john_smith")
        email = st.text_input("Email", key="new_user_email", placeholder="e.g., john@example.com")
        full_name = st.text_input("Full Name", key="new_user_fullname", placeholder="e.g., John Smith")
        password = st.text_input("Password", key="new_user_password", placeholder="Enter a secure password")
        
        roles = list(ROLE_PERMISSIONS.keys())
        role = st.selectbox(
            "Role",
            options=roles,
            key="new_user_role",
            index=next((i for i, r in enumerate(roles) if r.value == "viewer"), 0),
            format_func=lambda r: r.value.upper(),
        )
        
        col_submit, col_cancel = st.columns(2)
        
        with col_submit:
            if st.button("Create User", type="primary", width="stretch"):
                if username and email and password:
                    user_id = create_user(
                        username=username,
                        email=email,
                        password=password,
                        full_name=full_name or username,
                        role=role.value,
                    )
                    if user_id:
                        st.success(f"User {username} created successfully!")
                        st.session_state.show_create_user_modal = False
                        st.rerun()
                    else:
                        st.error("Failed to create user. Username or email may already exist.")
                else:
                    st.error("Username, email, and password are required.")
        
        with col_cancel:
            if st.button("Cancel", width="stretch"):
                st.session_state.show_create_user_modal = False
                st.rerun()