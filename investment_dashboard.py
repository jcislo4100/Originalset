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

        preview_df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0], header=None)
        header_row = 2 if "Account Name" in preview_df.iloc[2].values else 0
        df = pd.read_excel(uploaded_file, sheet_name=sheet_names[0], header=header_row)

        is_salesforce = "Account Name" in df.columns

        if is_salesforce:
            df = df.rename(columns={
                "Account Name": "Investment Name",
                "Total Investment": "Cost",
                "Share of Valuation": "Fair Value",
                "Valuation Date": "Date",
                "Parent Account": "Fund Name"
            })
            df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
            df["Fair Value"] = pd.to_numeric(df["Fair Value"], errors="coerce")
            if "Proceeds" in df.columns:
                df["Proceeds"] = pd.to_numeric(df["Proceeds"], errors="coerce").fillna(0)
            else:
                df["Proceeds"] = 0
            if "Date" not in df.columns:
                st.error("Missing required 'Valuation Date' field in uploaded Salesforce file.")
                st.stop()
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            if "Fund Name" not in df.columns:
                df["Fund Name"] = "Salesforce Import"

        else:
            possible_date_columns = [col for col in df.columns if isinstance(col, str) and ("date" in col.lower() or "year" in col.lower())]
            for col in possible_date_columns:
                try:
                    df["Date"] = pd.to_datetime(df[col], errors="coerce")
                    if df["Date"].notna().sum() > 0:
                        break
                except:
                    continue
            if "Date" not in df.columns:
                st.error("No date column found in standard Excel format.")
                st.stop()
            df = df.dropna(subset=["Date"])
            if "Fund Name" not in df.columns:
                df["Fund Name"] = "Standard Import"

        df["MOIC"] = df["Fair Value"] / df["Cost"]

        with st.sidebar:
            st.header("🔍 Filters")
            fund_filter = st.multiselect("Select Fund(s)", options=df["Fund Name"].unique(), default=df["Fund Name"].unique())
            year_range = st.slider("Select Year Range", int(df["Date"].dt.year.min()), int(df["Date"].dt.year.max()), (int(df["Date"].dt.year.min()), int(df["Date"].dt.year.max())))
            min_moic = float(df["MOIC"].min())
            max_moic = float(df["MOIC"].max())
            if min_moic == max_moic:
                min_moic -= 0.01
                max_moic += 0.01
            min_moic, max_moic = round(min_moic, 4), round(max_moic, 4)
            moic_range = st.slider("MOIC Range", min_value=min_moic, max_value=max_moic, value=(min_moic, max_moic))

        df = df[(df["Fund Name"].isin(fund_filter)) &
                (df["Date"].dt.year >= year_range[0]) &
                (df["Date"].dt.year <= year_range[1]) &
                (df["MOIC"] >= moic_range[0]) & (df["MOIC"] <= moic_range[1])]

        # Cash flow construction for IRR
        today = datetime.today()
        cashflow_df = pd.DataFrame()
        cashflow_df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        cashflow_df["Cash Flow"] = -df["Cost"]
        # Append fair value as final inflow
        cashflow_df = cashflow_df.append({"Date": today, "Cash Flow": df["Fair Value"].sum()}, ignore_index=True)
        cashflow_df = cashflow_df.groupby("Date")["Cash Flow"].sum().sort_index()

        irr = npf.irr(cashflow_df.values) if len(cashflow_df) >= 2 else np.nan
        irr_display = f"{irr * 100:.2f}%" if not np.isnan(irr) else "N/A"

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Amount Invested", f"${df['Cost'].sum():,.2f}")
        col2.metric("Total Fair Value", f"${df['Fair Value'].sum():,.2f}")
        col3.metric("Portfolio MOIC", f"{(df['Fair Value'].sum() / df['Cost'].sum()):.2f}")
        col4.metric("Estimated IRR", irr_display)

        st.markdown("---")
        st.subheader("📊 MOIC by Investment")
        st.dataframe(df[["Investment Name", "Fund Name", "Cost", "Fair Value", "MOIC"]].sort_values("MOIC", ascending=False))

        st.markdown("### 📈 Value vs. Cost Over Time")
        timeline = df.groupby("Date").agg({"Cost": "sum", "Fair Value": "sum"}).sort_index().cumsum().reset_index()
        fig = px.line(timeline, x="Date", y=["Cost", "Fair Value"], markers=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📊 MOIC by Fund")
        moic_fund = df.groupby("Fund Name").agg({"Cost": "sum", "Fair Value": "sum"}).reset_index()
        moic_fund["MOIC"] = moic_fund["Fair Value"] / moic_fund["Cost"]
        fig2 = px.bar(moic_fund.sort_values("MOIC", ascending=False), x="Fund Name", y="MOIC", text="MOIC",
                      title="MOIC by Fund (Weighted by Total Cost)", labels={"MOIC": "MOIC"})
        fig2.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig2.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig2, use_container_width=True)

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

