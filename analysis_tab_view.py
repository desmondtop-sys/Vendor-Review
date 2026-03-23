import streamlit as st

from backend.models import SecurityControl
from backend.permissions import Permission

from backend.charts import generate_report_pie_chart
from backend.report_utils import get_control_by_name

from defs import SECONDARY_TEXT_COLOR, INFO_BACKGROUND_COLOR, INFO_TEXT_COLOR
from frontend.styles import get_styles
from frontend.views.shared_components_view import render_security_score, render_vertical_divider
from frontend.utils import get_current_view_report, save_simulation_as_new_report
from frontend.state_manager import initialize_simulation, reset_sandbox, sync_sim_control, sync_sim_status
from frontend.auth_helpers import current_user_has_permission

def render_analysis_tools() -> None:
    """Render the analysis tools panel, chart, score, and simulation controls."""
    
    st.markdown(get_styles("analysis"), unsafe_allow_html=True)

    pie_chart_col, divider_col, save_sim_col = st.columns([0.65, 0.01, 0.34])

    # Skip pie chart if active report doesn't have controls (can happen with a blank report or if report failed to load)
    current_view_report = get_current_view_report()
    if not current_view_report or not current_view_report.controls:
        st.warning("No controls available to display. Ensure there is a report with requirements loaded to use the analysis tools.")
    else:
        with pie_chart_col:
            st.plotly_chart(generate_report_pie_chart(current_view_report), width='stretch')

        with divider_col:
            render_vertical_divider("45vh")
    
        with save_sim_col:
            with st.container():
                # Nudge the panel a little lower
                st.markdown('<div style="margin-top: 150px;"></div>', unsafe_allow_html=True)
                render_save_simulation_panel()

    render_sim_header()

    render_requirements()

    render_reset_sim_button()

def render_sim_header() -> None:
    

    col_title, col_security_score = st.columns([0.65, 0.35])
    with col_title:
        st.subheader("🏖️ Security Impact Sandbox")
        st.caption("Simulate different outcomes to see how they affect the final score.")
        st.caption("These parameters are reset upon reload.")
    with col_security_score:
        render_security_score(get_current_view_report())

def render_requirements() -> None:
    """Render interactive sandbox controls for each requirement in the report."""

    initialize_simulation()

    sim_report = st.session_state.simulation_report
    version = st.session_state.sim_version

    # Headers
    h_stat, h_info, h_slider, h_must_pass, h_check = st.columns([0.15, 0.3, 0.35, 0.1, 0.1])
    with h_stat:
        st.markdown('<p style="font-size:12px; font-weight:600; text-align:center;">Sim Status</p>', unsafe_allow_html=True)
    with h_info:
        st.markdown('<p style="font-size:12px; font-weight:600; text-align:center;">Requirements</p>', unsafe_allow_html=True)
    with h_must_pass:
        st.markdown('<p style="font-size:12px; font-weight:600; text-align:center;">Must Pass</p>', unsafe_allow_html=True)
    with h_slider:
        st.markdown('<p style="font-size:12px; font-weight:600; text-align:center;">Weights</p>', unsafe_allow_html=True)
    with h_check:
        st.markdown('<p style="font-size:12px; font-weight:600; text-align:center;">Include</p>', unsafe_allow_html=True)

    # Check for controls to render. If no report is loaded or report has no controls, this will safely render nothing instead of erroring out.
    controls = sim_report.controls if sim_report and sim_report.controls else []

    for control in controls:
        # UI logic to determine the display label
        if control.status == 1:
            current_idx = 0 # Pass: Dropdown points to 'Pass'
        elif control.must_pass:
            current_idx = 1 # Critical fail: Dropdown points to 'Fail'
        else:
            current_idx = 1 # Fail: Dropdown points to 'Fail'

        # 2. Description Row, then Simulation Row
        # Using a container to group the specific requirement's controls
        with st.container():
            col_stat, col_info, col_slider, col_must_pass, col_check = st.columns([0.2, 0.3, 0.3, 0.1, 0.1])

            with col_stat:
                stat_key = f"sim_v{version}_stat_{control.requirement}_{sim_report.id}"
                st.selectbox(
                    "Sim Status",
                    options=["✅ Pass", "❌ Fail"],
                    index=current_idx,
                    key=stat_key,
                    label_visibility="collapsed",
                    on_change=sync_sim_status,
                    args=(control.requirement, stat_key)
                )
            
            with col_info:
                # Displays Name + Original Weight
                # Pull original control from active report so users can compare sandbox edits against baseline values.
                original_control = get_control_by_name(st.session_state.active_report, control.name)
                # Safety: If control not found (e.g., after report switch), use simulation weight
                original_weight = original_control.weight if original_control else control.weight

                st.markdown(f"""
                    <p style="margin-bottom: 0px; font-weight: 600;">
                        <span class="vendor-label">{control.name}</span>
                    </p>
                    <p style="font-size: 0.85rem; color: {SECONDARY_TEXT_COLOR}; margin-top: -5px;">
                        Original Weight: {original_weight} pts
                    </p>
                """, unsafe_allow_html=True)
            
            # Create sliders to simulate changes to the weights
            with col_slider:

                # Versioned key forces Streamlit to rebuild slider state when simulation context changes.
                slider_key = f"sim_v{version}_{control.name}_{sim_report.id}"

                st.slider(
                    f"Weight for {control.name}",
                    min_value=0,
                    max_value=300,
                    value=int(control.weight),
                    key=slider_key,
                    label_visibility="collapsed",
                    on_change=sync_sim_control,
                    args=(control.name, slider_key)
                )

            # Column of checkboxes to set simulated "Must Pass" controls
            with col_must_pass:
                render_mustpass_checkbox(control)

            with col_check:
                render_include_checkbox(control)

        st.markdown("<div style='border-bottom: 1px solid rgba(255,255,255,0.05); margin: 10px 0;'></div>", unsafe_allow_html=True)

def render_save_simulation_panel() -> None:
    """Render the save-simulation panel for the analysis tools page."""

    st.markdown(
        """
        <div style="background-color: {bg_color}; border-radius: 10px; padding: 18px;">
            <div style="text-align: center; font-weight: 700; color: {text_color};">
                SAVE SIMULATION
            </div>
            <div style="text-align: center; font-size: 0.95rem; color: {text_color}; margin-top: 6px;">
                Save current sandbox settings as a new report version.
            </div>
        </div>
        """.format(bg_color=INFO_BACKGROUND_COLOR, text_color=INFO_TEXT_COLOR),
        unsafe_allow_html=True
    )

    if st.button("Save Simulation as New Report", type="primary", width='stretch', disabled=not current_user_has_permission(Permission.CREATE_REPORTS)):
        save_simulation_as_new_report()



def render_mustpass_checkbox(control: SecurityControl) -> None:
    """Render and synchronize the simulation must-pass checkbox for one control.

    Args:
        control (SecurityControl): Control currently being rendered.
    """
    
    sim_report = st.session_state.simulation_report
    version = st.session_state.sim_version
                
    must_key = f"sim_v{version}_must_{control.requirement}_{sim_report.id}"
    is_must = st.checkbox(
        "Must Pass", value=control.must_pass,
        key=must_key, label_visibility="collapsed"
    )
                
    # Sync Must Pass status with simulation controls
    if is_must != control.must_pass:
        control.must_pass = is_must
        st.rerun()

def render_include_checkbox(control: SecurityControl) -> None:
    """Render include checkbox and sync exclusion list for one control.

    Args:
        control (SecurityControl): Control currently being rendered.
    """

    report = st.session_state.simulation_report

    version = st.session_state.sim_version 
    
    check_key = f"sim_v{version}_check_{control.name}_{report.id}"

    is_active = st.checkbox(
        "Include", 
        value=(control.name not in report.excluded_names),
        key=check_key,
        label_visibility="collapsed"
    )
                
    # Sync logic for the exclusion list
    if not is_active and control.name not in report.excluded_names:
        report.excluded_names.append(control.name)
        st.rerun()
        
    elif is_active and control.name in report.excluded_names:
        report.excluded_names.remove(control.name)
        st.rerun()

def render_reset_sim_button() -> None:
    """Render the reset button that clears simulation sandbox state."""
    
    if st.button("♻️ Reset Simulation", width='stretch'):
        
        reset_sandbox()

        st.rerun()