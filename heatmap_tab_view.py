import streamlit as st
import json
import html
from backend.vendor_database import get_all_vendor_models, get_latest_report_for_vendor
from backend.config_manager import get_ai_requirements
from frontend.styles import get_styles

def render_heatmap_tab_view():
    """Render a heatmap showing all vendors and their control statuses."""

    st.markdown(get_styles("heatmap"), unsafe_allow_html=True)
    
    # Get all vendors
    vendors = get_all_vendor_models()
    
    if not vendors:
        st.info("No vendors found. Create a vendor to get started!")
        return
    
    st.header("Vendor Control Heatmap", anchor=False)

    
    st.markdown("<p style='font-size: 14px;'>Hover over control names for details</p>", unsafe_allow_html=True)
    
    # Collect data for heatmap
    heatmap_data = []
    all_control_names = set()
    control_requirements = {}
    
    for vendor in vendors:
        latest_report = get_latest_report_for_vendor(vendor.id)
        
        if latest_report:
            # Parse controls from JSON
            controls_data = json.loads(latest_report['controls_json'])
            
            # Create a map of control name to status
            controls_map = {c['name']: c['status'] for c in controls_data}

            for control in controls_data:
                name = control.get('name')
                requirement = control.get('requirement')
                if name and name not in control_requirements:
                    control_requirements[name] = requirement or name
            
            # Track all control names
            all_control_names.update(controls_map.keys())
            
            # Calculate score percentage
            score = latest_report['overall_score']
            possible = latest_report['possible_score']
            score_pct = round((score / possible * 100), 1) if possible > 0 else 0
            
            heatmap_data.append({
                'vendor_name': vendor.name,
                'controls': controls_map,
                'score': score,
                'possible': possible,
                'score_pct': score_pct
            })
        else:
            # Vendor with no reports
            heatmap_data.append({
                'vendor_name': vendor.name,
                'controls': {},
                'score': None,
                'possible': None,
                'score_pct': None
            })
    
    if not heatmap_data:
        st.info("No vendor data available.")
        return
    
    # Only show controls defined in requirements.json (in that order)
    # Use cached requirements from session (loaded at login)
    requirements_config = st.session_state.get("cached_ai_requirements", get_ai_requirements())
    controls = list(requirements_config.keys())
    
    # Build table
    html = build_heatmap_html(heatmap_data, controls, control_requirements, requirements_config)
    
    # Render the heatmap
    st.markdown(html, unsafe_allow_html=True)


def build_heatmap_html(heatmap_data: list, control_names: list, control_requirements: dict, requirements_config: dict) -> str:
    """Build an HTML table with color-coded cells for the heatmap.
    
    Args:
        heatmap_data: List of vendor data with controls and scores
        control_names: Sorted list of all control names
        control_requirements: Mapping of control names to requirement descriptions
        requirements_config: Full requirements config with weights
        
    Returns:
        str: HTML string for the heatmap table
    """

    def abbreviate_control_name(name: str) -> str:
        words = [w for w in name.replace("&", " ").replace("/", " ").split() if w]
        if len(words) >= 2:
            return "".join(word[0].upper() for word in words[:3])
        return name[:4].upper()
    
    # Start building the table
    html_parts = ['<div class="heatmap-container">']
    html_parts.append('<table class="heatmap-table">')
    
    # Header row
    html_parts.append('<thead><tr>')
    html_parts.append('<th class="vendor-col">Vendor</th>')
    
    for control in control_names:
        requirement = control_requirements.get(control, control)
        weight = requirements_config.get(control, {}).get('weight', 0)
        label = abbreviate_control_name(control)
        tooltip_text = f"{control} ({weight} pts)\n\n{requirement}"
        tooltip_text = html.escape(tooltip_text, quote=True)
        tooltip_text = tooltip_text.replace("\n", "&#10;")
        html_parts.append(
            f'<th class="control-col" title="{tooltip_text}">{label}</th>'
        )
    
    html_parts.append('<th class="score-col">Score</th>')
    html_parts.append('</tr></thead>')
    
    # Body rows
    html_parts.append('<tbody>')

    summary_counts = {
        name: {"pass": 0, "fail": 0} for name in control_names
    }
    
    for vendor_data in heatmap_data:
        html_parts.append('<tr>')
        
        # Vendor name column (sticky)
        html_parts.append(f'<td class="vendor-name">{vendor_data["vendor_name"]}</td>')
        
        # Control columns
        controls_map = vendor_data['controls']
        for control_name in control_names:
            if control_name in controls_map:
                status = controls_map[control_name]
                if status == 1:
                    cell_class = 'cell-pass'
                    cell_text = '✓'
                    summary_counts[control_name]["pass"] += 1
                else:
                    cell_class = 'cell-fail'
                    cell_text = '✗'
                    summary_counts[control_name]["fail"] += 1
            else:
                cell_class = 'cell-missing'
                cell_text = '—'
            
            html_parts.append(
                f'<td class="control-cell {cell_class}">{cell_text}</td>'
            )
        
        # Score column
        score = vendor_data['score']
        possible = vendor_data['possible']
        score_pct = vendor_data['score_pct']
        
        if score is not None and possible is not None:
            score_text = f'{score}/{possible} ({score_pct}%)'
        else:
            score_text = 'N/A'
        
        html_parts.append(f'<td class="score-cell">{score_text}</td>')
        
        html_parts.append('</tr>')

    html_parts.append('<tr class="summary-row">')
    html_parts.append('<td class="vendor-name summary-label">Summary</td>')

    for control_name in control_names:
        passes = summary_counts[control_name]["pass"]
        fails = summary_counts[control_name]["fail"]
        html_parts.append(
            f'<td class="control-cell summary-cell">{passes} | {fails}</td>'
        )

    html_parts.append('<td class="score-cell summary-cell">—</td>')
    html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)