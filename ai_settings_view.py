import streamlit as st
from streamlit_float import float_init, float_parent

from backend.charts import generate_settings_pie_chart
from backend.config_manager import get_ai_instructions, get_ai_requirements, get_threshold_settings, set_ai_instructions, set_ai_requirements, set_threshold_settings

from frontend.styles import get_styles
from frontend.utils import get_badge_values
from frontend.state_manager import mark_dirty

def render_ai_settings_page() -> None:
    """Render the full AI settings interface for prompt and requirement tuning."""
    
    # Initialize the float feature
    float_init()

    # Flag to check if we have unsaved changes
    # (used to change Save button color)
    if "is_dirty" not in st.session_state:
        st.session_state.is_dirty = False

    st.markdown(get_styles("ai_settings_page"), unsafe_allow_html=True)

    st.title("⚙️ AI Configuration", anchor=False)
    st.markdown("### Edit AI Prompting & Requirements")
    
    st.divider()

    new_instr = render_instructions()

    st.markdown("### Analysis Requirements")
    st.caption("Define the weights and descriptions for the security controls.")

    col_thresholds, col_spacer, col_chart = st.columns([0.3, 0.01, 0.69])

    # Allow the user to determine the pass/fail thresholds
    with col_thresholds:
        render_thresholds()

    # A vertical line using a div
    with col_spacer:
        st.markdown(
            """<div style="
            border-left: 
            1px solid #31333F; 
            height: 45vh; 
            margin-left: 5px;
            "></div>""", 
            unsafe_allow_html=True
        )
    
    # Display a pie chart of controls
    with col_chart:
        if "temp_requirements" not in st.session_state or st.session_state.temp_requirements is None:
            # Use cached requirements from session (loaded at login)
            st.session_state.temp_requirements = st.session_state.get("cached_ai_requirements", get_ai_requirements())
        st.plotly_chart(generate_settings_pie_chart(st.session_state.temp_requirements), width='stretch')
    
    col_spacer2, col_badge = st.columns([0.83, 0.17])
    
    with col_badge:
        # Render the badge below the pie chart
        badge_bg, badge_text, badge_label = get_badge_values()
        st.markdown(f"""
            <div style="
                background-color: {badge_bg}; 
                color: {badge_text}; 
                padding: 10px 20px; 
                border-radius: 15px; 
                font-weight: bold; 
                border: 1px solid {badge_text};
                font-size: 20px; 
                display: inline-block;
                margin-top: 10px;">
                Total Weight: {badge_label}
            </div>
            """, unsafe_allow_html=True)
    
    st.divider()

    updated_requirements = render_requirements_list()

    # Update session state for the live calculator
    st.session_state.temp_requirements = updated_requirements

    render_new_requirement_button()

    render_submit_button(new_instr, updated_requirements)

def render_instructions() -> str:
    """Render the editable instructions text area and return its current value.

    Returns:
        str: Current instruction text from the settings text area.
    """

    st.subheader("AI Instructions", anchor=False)
    st.caption("This controls the 'personality' and 'rules' the AI auditor follows.")

    # Use cached instructions from session (loaded at login)
    instructions = st.session_state.get("cached_ai_instructions", get_ai_instructions())

    # Calculate height of text area: number of lines * ~25 pixels + 50px buffer
    instr_line_count = instructions.count('\n') + 2
    instr_height = max(150, instr_line_count * 25)

    new_instr = st.text_area(
        "System Prompt", 
        value=instructions, 
        height=instr_height, 
        key="edit_instr",
        label_visibility="collapsed",
        on_change=mark_dirty
    )

    st.divider()

    return new_instr

def render_thresholds() -> None:
    """Render pass/fail threshold inputs and informational scoring guidance."""
    st.subheader("Thresholds", anchor=False)
    st.caption("Define the scoring zones for audit results.")

    # Use cached thresholds from session (loaded at login)
    thresholds = st.session_state.get("cached_threshold_settings", get_threshold_settings())
    pass_value = thresholds["pass_threshold"]
    fail_value = thresholds["fail_threshold"]
        
    new_pass = st.number_input(
        "Pass Threshold (%)", 
        value=pass_value, 
        min_value=1, 
        max_value=100, 
        step=5,
        on_change=mark_dirty, 
        key="threshold_pass"
    )
        
    new_fail = st.number_input(
        "Fail Threshold (%)", 
        value=fail_value, 
        min_value=0, 
        max_value=new_pass-1, 
        step=5,
        on_change=mark_dirty, 
        key="threshold_fail"
    )
        
    st.info(f"Scores between {new_fail}% and {new_pass}% will trigger 'NEEDS REVIEW'.")

def render_requirements_list() -> dict:
    """Render editable requirement rows and collect staged requirement values.

    Returns:
        dict: Updated requirement mapping built from current widget state.
    """
    updated_requirements = {}

    requirement_id = 1
    for key, data in st.session_state.temp_requirements.items():
        with st.container():
            # Standardized 5-column header for the requirement block
            cols = st.columns([0.12, 0.60, 0.11, 0.12, 0.05])
            
            with cols[0]:
                st.markdown(f'<p style="font-weight: 600; margin-top: 5px;">Requirement {requirement_id}:</p>', unsafe_allow_html=True)
                requirement_id += 1
            
            with cols[1]:
                # Requirement Name (now using the explicit name field)
                current_name = data.get("name", key)  # Use name field or fallback to key
                new_name = st.text_input(
                    "Name", value=current_name, key=f"name_{key}", 
                    label_visibility="collapsed", on_change=mark_dirty
                )
            
            with cols[2]:
                # Must Pass Toggle
                is_must = st.checkbox(
                    "Must Pass", value=data.get("must_pass", False), 
                    key=f"must_{key}", on_change=mark_dirty
                )
            
            with cols[3]:
                # Weight Input
                new_weight = st.number_input(
                    "Weight", value=int(data["weight"]), step=5, 
                    key=f"weight_{key}", label_visibility="collapsed", on_change=mark_dirty
                )
            with cols[4]:
                # Delete Button
                if st.button("🗑️", key=f"delete_{key}", on_click=mark_dirty):
                    # Delete immediately from session state and rerun so UI updates instantly
                    st.session_state.temp_requirements.pop(key, None)
                    for key_prefix in ["name_", "must_", "weight_", "desc_", "delete_"]:
                        st.session_state.pop(f"{key_prefix}{key}", None)
                    st.rerun()
            
            # Description Area
            new_desc = st.text_area(
                "Description", value=data["description"], 
                key=f"desc_{key}", label_visibility="collapsed", 
                height=80, on_change=mark_dirty
            )
            
            # Map the current UI state to the update dictionary
            # Keep the same key but update the name field
            updated_requirements[key] = {
                "name": new_name,
                "weight": new_weight,
                "description": new_desc,
                "must_pass": is_must
            }
            
            # Visual separator between control blocks
            st.markdown("<hr style='margin: 15px 0; opacity: 0.1;'>", unsafe_allow_html=True)

    return updated_requirements

def render_new_requirement_button() -> None:
    """Render button to append a new default requirement to staged settings."""

    if st.button("➕ Add New Requirement", width='stretch'):

        # Create a unique default name for the new requirement
        base_name = "New Requirement"
        idx = 1
        new_name = f"{base_name} {idx}"

        while new_name in st.session_state.temp_requirements:
            idx += 1
            new_name = f"{base_name} {idx}"
        
        # Add the new requirement with default values
        st.session_state.temp_requirements[new_name] = {
            "name": new_name,
            "weight": 10,
            "description": "Describe this requirement...",
            "must_pass": False
        }
        mark_dirty()

        st.rerun()

def render_submit_button(new_instr: str, updated_requirements: dict) -> None:
    """Render floating save button and persist all staged configuration values.

    Args:
        new_instr (str): Latest instruction text from the editor.
        updated_requirements (dict): Requirement configuration to persist.
    """

    button_container = st.container()

    with button_container:
        
        # --- Save Logic ---

        if st.session_state.is_dirty:
            type = "tertiary"
        else:
            type = "primary"

        if st.button("Save Configuration", type=type, width='stretch'):

            success_instr, msg_instr = set_ai_instructions(new_instr)
            success_reqs, msg_reqs = set_ai_requirements(updated_requirements)
            success_thresh, msg_thresh = set_threshold_settings(st.session_state.threshold_pass, st.session_state.threshold_fail)

            if success_instr and success_reqs and success_thresh:
                st.session_state.is_dirty = False
                st.success("Configuration Saved!")
                st.rerun()

        # This makes the button "float" at the bottom of the screen as you scroll
        float_parent("""
            bottom: 0px !important;
            left: inherit !important;
            right: 5% !important;
            width: auto !important;
            max-width: inherit !important;
            height: 80px !important;
            padding: 15px !important;
        """)