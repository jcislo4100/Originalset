# IRR and MOIC Calculator Prototype using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(layout="wide")
st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names

        target_sheet = "Schedule of investments"
        if target_sheet in sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0])
            st.warning(f"Sheet '{target_sheet}' not found. Loaded first available sheet: '{sheet_names[0]}'")

        # Try to identify a date column dynamically
        possible_date_columns = [col for col in df.columns if "date" in col.lower() or "year" in col.lower()]
        date_column = None
        for col in possible_date_columns:
            try:
                df["Date"] = pd.to_datetime(df[col], errors="coerce")
                if df["Date"].notna().sum() > 0:
                    date_column = col
                    break
            except:
                continue

        if date_column is None:
            st.error("Could not find a valid date column. Please include a column like 'Year - Month - Day'.")
        else:
            df = df.dropna(subset=["Date"])

            # Calculate MOIC
            df["MOIC"] = df["Fair Value"] / df["Cost"]

            # ---- FILTERS ----
            with st.sidebar:
                st.header("🔍 Filters")
                fund_filter = st.multiselect("Select Fund(s)", options=df["Fund Name"].unique(), default=df["Fund Name"].unique())
                year_range = st.slider("Select Year Range", int(df["Date"].dt.year.min()), int(df["Date"].dt.year.max()), (int(df["Date"].dt.year.min()), int(df["Date"].dt.year.max())))
                min_moic, max_moic = st.slider("MOIC Range", float(df["MOIC"].min()), float(df["MOIC"].max()), (float(df["MOIC"].min()), float(df["MOIC"].max())))

            df = df[(df["Fund Name"].isin(fund_filter)) &
                    (df["Date"].dt.year >= year_range[0]) &
                    (df["Date"].dt.year <= year_range[1]) &
                    (df["MOIC"] >= min_moic) & (df["MOIC"] <= max_moic)]

            # ---- IRR CALC ----
            irr_data = df[["Date", "Cost", "Proceeds", "Fair Value"]].copy()
            irr_data["Outflow"] = -irr_data["Cost"]
            irr_data["Inflow"] = irr_data["Proceeds"] + irr_data["Fair Value"]
            cashflows = irr_data.groupby("Date").agg({"Outflow": "sum", "Inflow": "sum"})
            cashflows_sorted = cashflows.sort_index()
            cashflow_series = (cashflows_sorted["Outflow"] + cashflows_sorted["Inflow"]).tolist()

            if len(cashflow_series) >= 2:
                irr = npf.irr(cashflow_series)
                irr_display = f"{irr * 100:.2f}%" if irr is not None else "N/A"
            else:
                irr_display = "Insufficient data"

            # ---- METRICS ----
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Amount Invested", f"${df['Cost'].sum():,.2f}")
            col2.metric("Total Fair Value", f"${df['Fair Value'].sum():,.2f}")
            col3.metric("Portfolio MOIC", f"{(df['Fair Value'].sum() / df['Cost'].sum()):.2f}")
            col4.metric("Estimated IRR", irr_display)

            st.markdown("---")
            st.subheader("📊 MOIC by Investment")
            st.dataframe(df[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC"]].sort_values("MOIC", ascending=False))

            # ---- CHARTS ----
            st.markdown("### 📈 Value vs. Cost Over Time")
            timeline = df.groupby("Date").agg({"Cost": "sum", "Fair Value": "sum"}).sort_index().cumsum().reset_index()
            fig = px.line(timeline, x="Date", y=["Cost", "Fair Value"], markers=True)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📊 MOIC Distribution")
            fig2 = px.histogram(df, x="MOIC", nbins=20, title="Distribution of MOIC across Investments")
            st.plotly_chart(fig2, use_container_width=True)

            # ---- PORTFOLIO INSIGHTS ----
            st.markdown("---")
            st.subheader("🧠 Portfolio Insights")

            top_moic = df.sort_values("MOIC", ascending=False).head(5)
            low_moic = df[df["MOIC"] < 1.0]
            unrealized_pct = df[df["Proceeds"] == 0].shape[0] / df.shape[0] * 100
            avg_holding_period = (datetime.now() - df["Date"]).dt.days.mean() / 365

            st.markdown(f"**Top 5 Investments by MOIC**")
            st.dataframe(top_moic[["Investment Name", "MOIC", "Fair Value"]])

            st.markdown(f"**Investments below 1.0x MOIC:** {low_moic.shape[0]} ({(low_moic.shape[0]/df.shape[0])*100:.1f}%)")
            st.markdown(f"**% of Unrealized Investments:** {unrealized_pct:.1f}%")
            st.markdown(f"**Avg. Holding Period:** {avg_holding_period:.2f} years")

            # ---- IRR OVER TIME ----
            st.markdown("### 📉 IRR Over Time")
            if "Gross IRR" in sheet_names:
                irr_df = pd.read_excel(uploaded_file, sheet_name="Gross IRR")
                irr_df["Date"] = pd.to_datetime(dict(year=irr_df["Snapshot Date (Year)"], month=irr_df["Snapshot Date (Month)"], day=1))
                fig3 = px.line(irr_df, x="Date", y="Gross IRR", title="Gross IRR Trend", markers=True)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.warning("No 'Gross IRR' sheet found to plot IRR trend.")

            # ---- EXPORT TO CSV ----
            st.markdown("---")
            st.subheader("📤 Export")
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download Portfolio Table as CSV",
                data=csv_buffer.getvalue(),
                file_name="portfolio_summary.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error loading file: {e}")
