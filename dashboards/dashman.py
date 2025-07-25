import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from datetime import timedelta

# ------------------- Simulate Handyman Job Data -------------------
np.random.seed(42)
technicians = ["Alex", "Jordan", "Taylor", "Morgan", "Casey"]
job_types = ["Plumbing", "Electrical", "Drywall", "Painting", "HVAC", "Carpentry"]
statuses = ["Completed", "Scheduled", "Cancelled", "No Show"]

today = pd.Timestamp("today").normalize()

# Generate 90 days of past jobs
past_jobs = pd.DataFrame({
    "date": pd.date_range(end=today - timedelta(days=1), periods=90).tolist(),
    "job_type": np.random.choice(job_types, 90),
    "technician": np.random.choice(technicians, 90),
    "status": np.random.choice(["Completed", "Cancelled", "No Show"], 90, p=[0.85, 0.1, 0.05]),
    "revenue": np.random.randint(100, 1000, 90)
})

# Generate 5–10 jobs for today
num_today = np.random.randint(5, 11)
today_jobs = pd.DataFrame({
    "date": [today] * num_today,
    "job_type": np.random.choice(job_types, num_today),
    "technician": np.random.choice(technicians, num_today),
    "status": ["Scheduled"] * num_today,
    "revenue": [0] * num_today
})

# Generate 7 days of upcoming jobs
upcoming_jobs = pd.DataFrame({
    "date": pd.date_range(start=today + timedelta(days=1), periods=7).tolist(),
    "job_type": np.random.choice(job_types, 7),
    "technician": np.random.choice(technicians, 7),
    "status": ["Scheduled"] * 7,
    "revenue": [0] * 7
})

df = pd.concat([past_jobs, today_jobs, upcoming_jobs], ignore_index=True)

# ------------------- Streamlit Dashboard -------------------
st.set_page_config(page_title="🔧 Handyman Dashboard", layout="wide")
st.title("🔧 Handyman Job Performance Dashboard")

# Date Filter Under Title
st.markdown("### 📅 Filter by Date Range")
start_date, end_date = st.date_input(
    "Select date range:",
    [df["date"].min().date(), df["date"].max().date()],
    min_value=df["date"].min().date(),
    max_value=df["date"].max().date()
)

# Filter DataFrame
df = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🏆 Technician Leaderboard", "🛠️ Job Types", "📅 Upcoming"])

with tab1:
    st.header("📊 Overview")

    total_jobs = len(df)
    completed_jobs = len(df[df["status"] == "Completed"])
    total_revenue = df["revenue"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs", total_jobs)
    col2.metric("Completed Jobs", completed_jobs)
    col3.metric("Revenue", f"${total_revenue:,.0f}")

    # Jobs per day
    daily = df[df["status"] == "Completed"].groupby("date")["revenue"].sum().reset_index()
    fig = px.bar(daily, x="date", y="revenue", title="Daily Revenue (Completed Jobs)", color="revenue", color_continuous_scale="turbo")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("🏆 Technician Leaderboard")
    tech_perf = df[df["status"] == "Completed"].groupby("technician").agg(
        jobs=("date", "count"),
        revenue=("revenue", "sum")
    ).reset_index().sort_values(by="revenue", ascending=False)
    fig = px.bar(tech_perf, x="revenue", y="technician", orientation="h", title="Technician Revenue", color="revenue", color_continuous_scale="turbo")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🛠️ Job Types Breakdown")
    type_summary = df[df["status"] == "Completed"].groupby("job_type").agg(
        jobs=("date", "count"),
        revenue=("revenue", "sum")
    ).reset_index().sort_values(by="jobs", ascending=False)

    col1, col2 = st.columns([1, 1])
    with col1:
        fig = px.pie(type_summary, names="job_type", values="jobs", title="Jobs by Type")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(type_summary)

with tab4:
    st.header("📅 Upcoming & Today’s Jobs")
    upcoming = df[(df["status"] == "Scheduled") & (df["date"] >= today)].sort_values("date")
    st.dataframe(upcoming.reset_index(drop=True))
