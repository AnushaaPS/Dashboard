import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import folium
from streamlit_folium import st_folium

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="DWLR Groundwater Dashboard", layout="wide")
st.title("DWLR Groundwater Monitoring & Analysis Dashboard")

# ----------------------------
# Hardcoded District Coordinates (approx centroids of Tamil Nadu districts)
# ----------------------------
district_coords = {
    "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Salem": (11.6643, 78.1460),
    "Erode": (11.3410, 77.7172),
    "Vellore": (12.9165, 79.1325),
    "Tirunelveli": (8.7139, 77.7567),
    "Thoothukudi": (8.7642, 78.1348),
    "Dindigul": (10.3624, 77.9695),
    "Thanjavur": (10.7870, 79.1378),
    "Kancheepuram": (12.8342, 79.7036),
    "Cuddalore": (11.7480, 79.7714),
    "Nagapattinam": (10.7650, 79.8449),
    "Ramanathapuram": (9.3639, 78.8395),
    "Krishnagiri": (12.5186, 78.2137),
    "Dharmapuri": (12.1357, 78.1582),
    "Villupuram": (11.9400, 79.5000),
    "Namakkal": (11.2202, 78.1652),
    "Karur": (10.9601, 78.0766),
    "Nilgiris": (11.4916, 76.7337),
    "Kanyakumari": (8.0883, 77.5385),
    "Tiruvallur": (13.1437, 79.9089),
    "Sivaganga": (9.8433, 78.4800),
    "Virudhunagar": (9.5680, 77.9624),
    "Ariyalur": (11.1381, 79.0786),
    "Perambalur": (11.2342, 78.8803),
    "Pudukkottai": (10.3797, 78.8208),
    "Tiruvarur": (10.7720, 79.6368),
    "Tiruppur": (11.1085, 77.3411)
}

# ----------------------------
# Helper Functions
# ----------------------------
def normalize_df(df, filename):
    """Normalize column names and add Year if in filename"""
    df.columns = df.columns.str.strip().str.replace("\n", " ")

    # Rename standard columns
    rename_map = {
        "No of wells Monitored": "Wells_Monitored",
        "S No": "SNo"
    }
    df.rename(columns=rename_map, inplace=True)

    # Extract year from filename
    year = "".join([c for c in filename if c.isdigit()])
    if year:
        df["Year"] = int(year)
    else:
        df["Year"] = None

    # If no lat/long, inject synthetic coords
    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        df["Latitude"] = df["District"].map(lambda d: district_coords.get(d, (11.0, 78.0))[0])
        df["Longitude"] = df["District"].map(lambda d: district_coords.get(d, (11.0, 78.0))[1])

    return df


def calc_stats(df):
    """Basic descriptive stats for water levels"""
    return df.groupby(["District", "Year"]).agg(
        Mean_Min=("Minimum", "mean"),
        Mean_Max=("Maximum", "mean"),
        Median_Min=("Minimum", "median"),
        Median_Max=("Maximum", "median"),
        Range_MinMax=("Maximum", lambda x: x.max() - x.min())
    ).reset_index()


# ----------------------------
# Main App
# ----------------------------
if uploaded_files := st.file_uploader("📂 Upload DWLR Dataset(s) (CSV with standardized headers)", type="csv", accept_multiple_files=True):
    dfs = []
    for f in uploaded_files:
        df = pd.read_csv(f)
        df = normalize_df(df, f.name)
        dfs.append(df)
    df_all = pd.concat(dfs, ignore_index=True)

    # Sidebar Filters
    st.sidebar.header("Filters")
    years = sorted(df_all["Year"].dropna().unique())
    districts = sorted(df_all["District"].dropna().unique())
    selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years)
    selected_districts = st.sidebar.multiselect("Select District(s)", districts, default=districts)

    df_filtered = df_all[
        (df_all["Year"].isin(selected_years)) & 
        (df_all["District"].isin(selected_districts))
    ]

    # ----------------------------
    # Basic Descriptive Statistics
    # ----------------------------
    st.subheader("Descriptive Statistics")
    if not df_filtered.empty:
        stats_df = calc_stats(df_filtered)
        st.dataframe(stats_df)
    else:
        st.warning("No data available for the selected filters.")

    # ----------------------------
    # Yearly Trends
    # ----------------------------
    st.subheader("Yearly Trends")
    if not df_filtered.empty:
        yearly_trend = df_filtered.groupby("Year")[["Minimum", "Maximum"]].mean().reset_index()
        fig_yearly = px.bar(yearly_trend, x="Year", y=["Minimum", "Maximum"],
                            barmode="group", title="Yearly Avg Min & Max Water Levels")
        st.plotly_chart(fig_yearly, use_container_width=True)

    # ----------------------------
# Recharge / Decline Patterns
# ----------------------------
    st.subheader("Recharge / Decline Analysis")

# Group by District & Year, compute average minimum level
    yearly_change = (
    df_filtered.groupby(["District", "Year"])["Minimum"]
    .mean()
    .reset_index()
    .sort_values(["District", "Year"])
    )

# Compute difference from previous year (Δ Water Level)
    yearly_change["DeltaWL"] = yearly_change.groupby("District")["Minimum"].diff()

    if not yearly_change["DeltaWL"].isna().all():
    # Show table with arrows for quick insights
        trend_table = yearly_change.copy()
        trend_table["Trend"] = trend_table["DeltaWL"].apply(
            lambda x: "⬆️ Recharge" if x > 0 else ("⬇️ Decline" if x < 0 else "➖ Stable")
        )
        st.dataframe(trend_table)

    # Plot recharge/decline per district over years
        fig_delta_year = px.bar(
            yearly_change,
            x="Year",
            y="DeltaWL",
            color="District",
            barmode="group",
            title="Year-over-Year Δ Water Level (Recharge vs Decline)"
        )
        st.plotly_chart(fig_delta_year, use_container_width=True)
    else:
        st.info("⚠️ Not enough yearly data to calculate recharge/decline.")

    # ----------------------------
    # Spatial Comparison (Map)
    # ----------------------------
    st.subheader("Spatial Comparison of Stations")
    avg_depth = df_filtered.groupby(["District", "Latitude", "Longitude"])["Minimum"].mean().reset_index()
    m = folium.Map(location=[avg_depth["Latitude"].mean(), avg_depth["Longitude"].mean()], zoom_start=7)
    for _, row in avg_depth.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=6,
            popup=f"{row['District']} - Depth: {row['Minimum']:.2f} m",
            color="blue" if row["Minimum"] < 5 else "red",
            fill=True,
            fill_opacity=0.7
        ).add_to(m)
    st_folium(m, width=700, height=500)

    # ----------------------------
    # Depth Distribution
    # ----------------------------
    st.subheader("Depth Distribution by Ranges")
    depth_cols = [c for c in df_filtered.columns if "%" in c]
    if depth_cols:
        depth_df = df_filtered.melt(id_vars=["District", "Year"], value_vars=depth_cols,
                                    var_name="DepthRange", value_name="Percentage")
        fig_depth = px.bar(depth_df, x="District", y="Percentage", color="DepthRange",
                           barmode="stack", facet_col="Year", title="Depth Distribution by District & Year")
        st.plotly_chart(fig_depth, use_container_width=True)
    else:
        st.info("⚠️ No depth range percentage columns found for distribution analysis.")

    # ----------------------------
    # Statewise Summary
    # ----------------------------
    st.subheader("State-wise Water Level Summary")
    if not df_filtered.empty:
        state_summary = df_filtered.groupby("Year")[["Minimum", "Maximum"]].mean().reset_index()
        fig_state = px.line(state_summary, x="Year", y=["Minimum", "Maximum"], markers=True,
                            title="State-wise Avg Min & Max Water Levels")
        st.plotly_chart(fig_state, use_container_width=True)

#else:
    #st.info("📂 Please upload DWLR station CSV dataset(s) to begin analysis.")

