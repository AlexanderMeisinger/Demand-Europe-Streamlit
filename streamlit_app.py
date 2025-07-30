# Visualization of PyPSA-Eur results using Streamlit
# Author: Alexander Meisinger
# Base: https://github.com/fneum/spatial-sector-dashboard and https://github.com/PyPSA/pypsa-eur

import streamlit as st
import pandas as pd
import xarray as xr
import yaml
from matplotlib.colors import to_rgba
from contextlib import suppress
import plotly.express as px
from PIL import Image

# Import helper functions (defined in helpers.py)
from helpers import rename_techs_energy_balance, prepare_colors, rename_techs_h2_balance, rename_tech_capacity

# Load configuration (defined in data/config.yaml)
with open("data/config.yaml", encoding='utf-8') as file:
    config = yaml.safe_load(file)

# Define preferred column ordering for plotting
preferred_order_energy_balance = pd.Index(config['preferred_order_energy_balance'])


## Streamlit Page Settings
# Webpage title
st.set_page_config(
    page_title='H2Global meets Africa',
    layout="wide"
)

style = '<style>div.block-container{padding-top:.5rem; padding-bottom:0rem; padding-right:1.2rem; padding-left:1.2rem}</style>'
st.write(style, unsafe_allow_html=True)

# SVG als Text (z. B. aus einer Datei oder als String)
svg_path = "BMFTR_Logo.svg"
with open(svg_path, "r") as f:
    svg = f.read()

# Sidebar
with st.sidebar:
    st.components.v1.html(
        f'<div style="margin-left:-20px">{svg}</div>', 
        height=150
    )
    
    st.title("H2Global meets Africa: Energy demand modelling in Germany and the EU")

    st.markdown("""
        **Institute for Energy Networks and Energy Storage, OTH Regensburg**
    """)

    # Choose between regional views
    pages = [
        "Europe",
        "Germany"
    ]
    display = st.selectbox("Region", pages, help="Choose your view on the system.")

    sel = {}

    # Sensitivity scenario selections
    choices = {0: "2 °C", 1: "1.5 °C"}
    sel["low_carbon"] = st.radio(
        ":thermometer: Temperature rise",
        choices,
        format_func=lambda x: choices[x],
        horizontal=True,
        help='Left button must be selected for all other choices in this segment.',
    )

    choices = {0: "yes", 1: "no"}
    sel["high_carbon"] = st.radio(
        ":factory: Climate goals",
        choices,
        format_func=lambda x: choices[x],
        horizontal=True,
        help='Left button must be selected for all other choices in this segment.',
    )

    choices = {0: "No", 1: "Yes"}
    sel["low_h2cost"] = st.radio(
        "💰 Low H2 cost",
        choices,
        format_func=lambda x: choices[x],
        horizontal=True,
        help='Left button must be selected for all other choices in this segment.',
    )

    choices = {0: "no", 1: "yes"}
    sel["grid_freeze"] = st.radio(
        "🧊 Grid freeze",
        choices,
        format_func=lambda x: choices[x],
        horizontal=True,
        help='Left button must be selected for all other choices in this segment.',
    )

    choices = {0: "no", 1: "yes"}
    sel["high_h2demand"] = st.radio(
        "💧 High H2 demand",
        choices,
        format_func=lambda x: choices[x],
        horizontal=True,
        help='Left button must be selected for all other choices in this segment.',
    )

    # Count how many sensitivity options are active
    number_sensitivities = sel["low_carbon"] + sel["low_h2cost"] + sel["grid_freeze"] + sel["high_h2demand"] + sel["high_carbon"]

    # Additional information
    with st.expander("Details"):
         st.write("""
             All results were created using the open European energy system model
             PyPSA-Eur-Sec. The model covers all energy sectors including
             electricity, buildings, transport, agriculture and industry at high
             spatio-temporal resolution. The model code is available on
             [Github](http://github.com/pypsa/pypsa-eur-sec).
             """)

## Main view of results: Germany or Europe
# Europe
if (display == "Europe") and (number_sensitivities <= 1):

    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Europe")

    # Select scenario
    choices = config["EU_scenarios"]
    idx = st.selectbox("View", choices, format_func=lambda x: choices[x], label_visibility='hidden')

    # Load result file for Europe from PyPSA-Eur
    ds = xr.open_dataset("data/EU_scenarios_streamlit.nc")

    # Filter the dataset by selected sensitivities
    accessors = {k: v for k, v in sel.items() if k not in ['power_grid', 'hydrogen_grid']}
    df = ds[idx].sel(**accessors, drop=True).to_dataframe().squeeze().unstack(level=0).dropna(axis=1)

    # Flatten index (used for plotting)
    df.index = ["".join(str(col)).strip() for col in df.index.values]

    # Preprocessing results depending on output type
    if idx == "energy":
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.groupby(axis=1, level=0).sum()

        to_drop = df.columns[(df.abs() < 50).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]
    elif idx == "hydrogen": 
        df.columns = df.columns.map(rename_techs_h2_balance)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 50).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
    elif idx == "storage" or idx == "generation" or idx == "conversion":
        df.columns = df.columns.map(rename_tech_capacity)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] 
        df.drop(columns=to_drop, inplace=True)
    else:
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] 
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]

    # Clean up redundant storage technologies
    if idx == 'storage':
         df.drop("co2", axis=1, inplace=True, errors="ignore")
         df.drop("co2 sequestered", axis=1, inplace=True, errors="ignore")
         df.drop("electricity distribution grid", axis=1, inplace=True, errors="ignore")
         df.drop("methanol", axis=1, inplace=True, errors="ignore")
         df.drop("oil", axis=1, inplace=True, errors="ignore")
         df.drop("oil refining", axis=1, inplace=True, errors="ignore")
         df.drop("solar rooftop", axis=1, inplace=True, errors="ignore")
         df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("Solar", axis=1, inplace=True, errors="ignore")
         df.drop("biogas", axis=1, inplace=True, errors="ignore")
         df.drop("gas", axis=1, inplace=True, errors="ignore")
         df.drop("ammonia store", axis=1, inplace=True, errors="ignore")
         df.drop("solid biomass transport", axis=1, inplace=True, errors="ignore")
         df.drop("methane", axis=1, inplace=True, errors="ignore")
         df.drop("solar PV", axis=1, inplace=True, errors="ignore")
         df.drop("others", axis=1, inplace=True, errors="ignore")
         df.drop("hydrogen", axis=1, inplace=True, errors="ignore")

    # Clean up redundant generation technologies
    if idx == 'generation':
        df.drop("biogas", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")

    # Clean up redundant conversion technologies
    if idx == 'conversion':
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass transport", axis=1, inplace=True, errors="ignore")


    # Plotting
    colors = prepare_colors(config) # Get color map from config
    color = [colors[c] for c in df.columns] # Match color to column order
    unit = choices[idx].split(" (")[1][:-1] # Extract unit from scenario name

    # Define bar chart
    plot = px.bar(
    df,
    x=df.index,  
    y=df.columns,  
    color_discrete_sequence=color,
    labels={"value": f"{choices[idx]}", "index": ""},
    height=720,
    )

    # Update layout for font scaling and legend
    plot.update_layout(
        font=dict(size=18),
        xaxis=dict(
            title=dict(font=dict(size=18)),
            tickfont=dict(size=16),
        ),
        yaxis=dict(
            title=dict(font=dict(size=18)),
            tickfont=dict(size=16),
            tickformat=".0f"
        ),
        legend=dict(
            title=dict(text=""),
            font=dict(size=16),
        ),
    )

    # Add hover tooltips
    plot.update_traces(
        hovertemplate="Technology: %{x}<br>Value: %{y:.2f}<br>"
    )

    # Display the Plotly chart in Streamlit
    st.plotly_chart(plot, use_container_width=True)

## Main view of results: Germany or Europe
# Germany
if (display == "Germany") and (number_sensitivities <= 1):

    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Germany")

    # Select scenario
    choices = config["DE_scenarios"]
    idx = st.selectbox("View", choices, format_func=lambda x: choices[x], label_visibility='hidden')

    # Load result file for Germany from PyPSA-Eur
    ds = xr.open_dataset("data/DE_scenarios_streamlit.nc")

    # Filter the dataset by selected sensitivities
    accessors = {k: v for k, v in sel.items() if k not in ['power_grid', 'hydrogen_grid']}
    df = ds[idx].sel(**accessors, drop=True).to_dataframe().squeeze().unstack(level=0).dropna(axis=1)

    # Flatten index (used for plotting)
    df.index = ["".join(str(col)).strip() for col in df.index.values]

    # Preprocessing results depending on output type
    if idx == "energy":
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]
    elif idx == "hydrogen": 
        df.columns = df.columns.map(rename_techs_h2_balance)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
    elif idx == "storage" or idx == "generation" or idx == "conversion":
        df.columns = df.columns.map(rename_tech_capacity)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
    else:
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.groupby(axis=1, level=0).sum()
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)]
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]

    # Clean up redundant storage technologies
    if idx == 'storage':
         df.drop("co2 sequestered", axis=1, inplace=True, errors="ignore")
         df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("biogas", axis=1, inplace=True, errors="ignore")
         df.drop("gas", axis=1, inplace=True, errors="ignore")
         df.drop("ammonia store", axis=1, inplace=True, errors="ignore")
         df.drop("hydrogen", axis=1, inplace=True, errors="ignore")

    # Clean up redundant generation technologies
    if idx == 'generation':
        df.drop("biogas", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")

    # Clean up redundant conversion technologies
    if idx == 'conversion':
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biomass", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass transport", axis=1, inplace=True, errors="ignore")
        
    # Plotting
    colors = prepare_colors(config) # Get color map from config
    color = [colors[c] for c in df.columns] # Match color to column order
    unit = choices[idx].split(" (")[1][:-1] # Extract unit from scenario name

    # Define bar chart
    plot = px.bar(
    df,
    x=df.index,
    y=df.columns,
    color_discrete_sequence=color,
    labels={"value": f"{choices[idx]}", "index": ""},
    height=720,
    )

    # Update layout for font scaling and legend
    plot.update_layout(
        font=dict(size=18),
        xaxis=dict(
            title=dict(font=dict(size=18)),
            tickfont=dict(size=16),
        ),
        yaxis=dict(
            title=dict(font=dict(size=18)),
            tickfont=dict(size=16),
            tickformat=".1f" if idx =="storage" else ".0f"
        ),
        legend=dict(
            title=dict(text=""),
            font=dict(size=16),
        ),
    )

    # Add hover tooltips
    plot.update_traces(
        hovertemplate="Technology: %{x}<br>Value: %{y:.2f}<br>"
    )

    # Display the Plotly chart in Streamlit
    st.plotly_chart(plot, use_container_width=True)

# Sensitivity check
if number_sensitivities > 1:
    st.write("")
    st.write("")

    message = "Sorry, you can only choose one additional sensitivity in the lower block of the left panel!"
    st.error(message, icon="🚨")
