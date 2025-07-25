import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import plotly.express as px


# Load pre-aggregated analytics CSVs or compute from base CSVs
fub = pd.read_csv("data/follow_up_boss.csv", parse_dates=["created_at", "last_activity", "last_stage_change", "next_task_due"])
dotloop = pd.read_csv("data/dotloop.csv", parse_dates=["expected_close_date", "actual_close_date"])
quickbooks = pd.read_csv("data/quickbooks.csv", parse_dates=["invoice_date", "paid_date"])
ads = pd.read_csv("data/ads.csv")
agents = pd.read_csv("data/agents.csv")
mls = pd.read_csv("data/mls.csv", parse_dates=["list_date", "close_date"])

st.set_page_config(page_title="Real Estate Performance Dashboard", layout="wide")

# Title
st.title("🏠 Real Estate Analytics Dashboard")

tabs = st.tabs(["Overview", "Agent Performance", "Marketing ROI", "Territory Insights", "Lead Scoring"])

# ---------- OVERVIEW TAB ----------
with tabs[0]:
    st.header("📍 Business Overview")

    st.subheader("Commission Forecast (Under Contract)")
    under_contract_ids = dotloop[dotloop["deal_status"] == "Under Contract"]["loop_id"]
    forecast = quickbooks[quickbooks["deal_id"].isin(under_contract_ids)]
    st.metric("💰 Expected Commission", f"${forecast['net_commission'].sum():,.0f}")

    st.subheader("Agent Leaderboard (Closed Deals)")
    # Merge dotloop + quickbooks
    closed_deals = dotloop[dotloop["deal_status"] == "Closed"]
    leaderboard = closed_deals.merge(quickbooks, left_on="loop_id", right_on="deal_id")

    # Add agent names
    leaderboard = leaderboard.merge(agents, on="agent_id", how="left")

    # Create leaderboard summary
    agent_summary = leaderboard.groupby("full_name")["net_commission"].sum().reset_index().sort_values(
        by="net_commission", ascending=False)
    st.altair_chart(
        alt.Chart(agent_summary).mark_bar().encode(
            x=alt.X("net_commission:Q", title="Total Commission"),
            y=alt.Y("full_name:N", sort="-x"),
            color="full_name:N"
        ),
        use_container_width=True
    )

    st.subheader("Pipeline Stage Breakdown")
    stage_counts = fub["stage"].value_counts().reset_index()
    stage_counts.columns = ["stage", "count"]
    chart = alt.Chart(stage_counts).mark_bar().encode(
        x=alt.X("stage:N", sort="-y"),
        y="count:Q",
        color="stage:N"
    )
    st.altair_chart(chart, use_container_width=True)


# ---------- AGENT PERFORMANCE ----------
with tabs[1]:
    st.header("🏆 Agent Performance Tracker")
    selected_agent = st.selectbox("Select an Agent", agents["full_name"].unique())
    agent_id = agents[agents["full_name"] == selected_agent]["agent_id"].values[0]

    leads = fub[fub["agent_assigned"] == selected_agent]
    deals = dotloop[dotloop["listing_agent_id"] == agent_id]
    commissions = quickbooks[quickbooks["agent_id"] == agent_id]

    st.metric("Leads", len(leads))
    st.metric("Deals Closed", len(deals[deals["deal_status"] == "Closed"]))
    st.metric("Total Commission", f"${commissions['net_commission'].sum():,.0f}")

    if not deals.empty:
        deals["close_time"] = (pd.to_datetime(deals["actual_close_date"]) - pd.to_datetime(deals["expected_close_date"])).dt.days
        st.metric("Avg Close Delay", f"{deals['close_time'].mean():.1f} days")

# ---------- MARKETING ROI ----------
with tabs[2]:
    st.header("📣 Campaign Performance")

    st.subheader("Cost per Closed Deal")
    merged = ads.copy()
    merged["closed_deals"] = merged["leads_generated"] // 4  # simulate closure rate
    merged["cost_per_closed_deal"] = merged["ad_spend"] / merged["closed_deals"]
    merged = merged[merged["closed_deals"] > 0]

    # Simulate revenue per closed deal
    merged["net_commission"] = merged["closed_deals"] * 5000  # assume $5k per deal
    merged["roi"] = (merged["net_commission"] - merged["ad_spend"]) / merged["ad_spend"]


    # 📈 Bubble Chart: ROI vs CPCD
    st.subheader("📈 ROI vs Cost per Closed Deal (Interactive)")
    fig = px.scatter(
        merged,
        x="cost_per_closed_deal",
        y="roi",
        color="platform",
        size="closed_deals",
        hover_data=["utm_campaign", "platform", "ad_spend", "closed_deals", "net_commission", "roi"],
        labels={
            "cost_per_closed_deal": "Cost per Closed Deal",
            "roi": "ROI",
            "platform": "Ad Platform"
        },
        title="Campaign ROI by Platform"
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)



    # 📊 Bar chart: CPCD
    st.altair_chart(
        alt.Chart(merged).mark_bar().encode(
            x=alt.X("utm_campaign:N", title="Campaign"),
            y=alt.Y("cost_per_closed_deal:Q", title="Cost per Closed Deal"),
            color="platform:N"
        ).properties(width=700),
        use_container_width=True
    )

    # Compute leads-to-close ratio
    merged["leads_to_close_ratio"] = merged["closed_deals"] / merged["leads_generated"]

    st.subheader("📈 Leads-to-Close Ratio vs ROI")

    fig_ratio_roi = px.scatter(
        merged,
        x="leads_to_close_ratio",
        y="roi",
        size="closed_deals",
        color="platform",  # or "utm_campaign"
        hover_data=["utm_campaign", "leads_generated", "closed_deals", "roi", "ad_spend", "platform"],
        labels={
            "leads_to_close_ratio": "Leads-to-Close Ratio",
            "roi": "Return on Investment",
        },
        title="Campaign Efficiency: Leads-to-Close vs ROI",
        color_discrete_sequence=px.colors.sequential.Turbo
    )

    fig_ratio_roi.update_layout(height=500)
    st.plotly_chart(fig_ratio_roi, use_container_width=True)

    # 📋 Table view
    st.dataframe(merged[[
        "utm_campaign", "platform", "leads_generated", "closed_deals",
        "ad_spend", "cost_per_closed_deal", "net_commission", "roi"
    ]])
# ---------- TERRITORY INSIGHTS ----------
with tabs[3]:
    st.header("🌍 Territory Insights")

    # city revenue bar chart
    by_city = mls[mls["status"] == "Closed"].groupby("city").agg(
        listings=("mls_id", "count"),
        avg_sale_price=("sale_price", "mean")
    ).reset_index().sort_values(by="listings", ascending=False)

    st.subheader("Most Expensive Cities by Closed Listings")
    st.altair_chart(
        alt.Chart(by_city).mark_bar().encode(
            x="avg_sale_price:Q",
            y=alt.Y("city:N", sort="-x"),
            color="avg_sale_price:Q"
        ),
        use_container_width=True
    )
    # Use Streamlit columns for side-by-side layout
    col1, col2 = st.columns([1.3, 1.2])  # Adjust width ratio if needed

    with col1:
        st.write("📋 Listings Table")
        st.dataframe(by_city)

    with col2:
        st.write("📊 Total Listings by City")
        fig_pie = px.pie(
            by_city,
            names="city",
            values="listings",
            color_discrete_sequence=px.colors.sequential.Turbo,
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)


    # Load city-level summary with lat/lon
    # City coords for heatmap
    city_coords = {
        "Babylon": {"lat": 40.695, "lon": -73.325},
        "Hempstead": {"lat": 40.706, "lon": -73.626},
        "Huntington": {"lat": 40.868, "lon": -73.425},
        "Freeport": {"lat": 40.657, "lon": -73.582},
        "Brookhaven": {"lat": 40.779, "lon": -72.915},
        "Islip": {"lat": 40.730, "lon": -73.190},
        "Smithtown": {"lat": 40.855, "lon": -73.200}
    }

    by_city = mls[mls["status"] == "Closed"].groupby("city").agg(
        listings=("mls_id", "count"),
        avg_sale_price=("sale_price", "mean")
    ).reset_index().sort_values(by="listings", ascending=False)

    by_city["lat"] = by_city["city"].map(lambda x: city_coords.get(x, {}).get("lat", np.nan))
    by_city["lon"] = by_city["city"].map(lambda x: city_coords.get(x, {}).get("lon", np.nan))

    st.subheader("📍 Territory Heatmap (Long Island)")
    fig_map = px.scatter_mapbox(
        by_city.dropna(subset=["lat", "lon"]),
        lat="lat",
        lon="lon",
        size="listings",
        color="avg_sale_price",
        hover_name="city",
        size_max=42,
        zoom=9,
        mapbox_style="open-street-map",  # ← this adds a clear styled background
        color_continuous_scale = "Turbo"
    )

    st.plotly_chart(fig_map, use_container_width=True)

# ---------- LEAD SCORING ----------
with tabs[4]:
    st.header("🎯 Lead Scoring Model (Simulated)")
    fub["lead_score"] = pd.Series(np.random.rand(len(fub)))  # simulate 0–1 scores
    top_leads = fub.sort_values("lead_score", ascending=False).head(10)

    st.write("Top 10 Most Promising Leads")
    st.dataframe(top_leads[["full_name", "email", "lead_source", "stage", "lead_score"]])
