import streamlit as st
import plotly.express as px

from defs import FAIL_CHART_COLOR, PASS_CHART_COLOR

from backend.models import Report

def generate_pie_chart(labels: list[str], values: list[int | float]):
    """Create a base pie chart for requirement labels and weights.

    Args:
        labels (list[str]): Requirement names used as pie slice labels.
        values (list[int | float]): Numeric values for each corresponding label.

    Returns:
        plotly.graph_objects.Figure: Configured Plotly pie chart figure.
    """

    # Initialize chart
    fig = px.pie(
        names=labels, 
        values=values, 
        title="Requirement Weight Distribution", 
        hole=0.2
    )
    # Update colors and font settings
    fig.update_traces(
        textinfo='value+label',
        textfont_size=10,
        textposition='inside',
        insidetextorientation='horizontal'
    )

    return fig

def generate_report_pie_chart(report: Report):
    """Build a report-specific pie chart using control weights and statuses.

    Args:
        report (VendorReport): Report object containing controls and excluded
            names.

    Returns:
        plotly.graph_objects.Figure: Pie chart where each included control is a
        slice and color indicates pass/fail status.

    Notes:
        - Controls listed in "report.excluded_names" are omitted.
        - Slice colors are red for failed controls (status "0") and green for
          passed controls (status "1").
    """

    # Get controls in the report
    controls = [c for c in report.controls if c.name not in report.excluded_names]
    
    # Extract labels and values
    labels = [control.name for control in controls]
    values = [control.weight for control in controls]

    chart = generate_pie_chart(labels, values)

    # Create a color list: Red for failed (0), Green for passed (1)
    colors = [FAIL_CHART_COLOR if c.status == 0 else PASS_CHART_COLOR for c in controls]

    chart.update_traces(
        marker=dict(colors=colors)
    )

    return chart

def generate_settings_pie_chart(requirements: dict):
    """Create a settings-page pie chart from configured or live requirement weights.

    Args:
        requirements (dict): Requirement config keyed by requirement name with
            default metadata including "weight".

    Returns:
        plotly.graph_objects.Figure: Pie chart reflecting current UI weights,
        preferring values from "st.session_state" when available.
    """

    labels = []
    values = []
    
    for key, data in requirements.items():
        weight_key = f"weight_{key}"
        
        # Check if the widget has a value in session state yet
        if weight_key in st.session_state:
            live_weight = st.session_state[weight_key]
        else:
            live_weight = data.get("weight", 0)
            
        labels.append(key)
        values.append(live_weight)

    return generate_pie_chart(labels, values)