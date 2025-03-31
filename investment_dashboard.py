# IRR and MOIC Calculator Prototype using Streamlit

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

st.title("📈 Investment Performance Dashboard")

uploaded_file = st.file_uploader("Upload Investment Excel", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Schedule of investments")

    st.subheader("Raw Investment Data")
    st.dataframe(df)

    # Clean date
    df["Date"] = pd.to_datetime(df["Year - Month - Day"].astype(str), errors="coerce")
    df = df.dropna(subset=["Date"])

    # Calculate MOIC
    df["MOIC"] = df["Fair Value"] / df["Cost"]

    # IRR Calculation requires cash flows
    irr_data = df[["Date", "Cost", "Proceeds", "Fair Value"]].copy()
    irr_data["Outflow"] = -irr_data["Cost"]
    irr_data["Inflow"] = irr_data["Proceeds"] + irr_data["Fair Value"]
    
    cashflows = irr_data.groupby("Date").agg({"Outflow": "sum", "Inflow": "sum"})
    cashflows_sorted = cashflows.sort_index()
    cashflow_series = (cashflows_sorted["Outflow"] + cashflows_sorted["Inflow"]).tolist()

    if len(cashflow_series) >= 2:
        irr = np.irr(cashflow_series)
        irr_display = f"{irr * 100:.2f}%" if irr is not None else "N/A"
    else:
        irr_display = "Insufficient data"

    st.subheader("Summary Metrics")
    st.metric("Total Amount Invested", f"${df['Cost'].sum():,.2f}")
    st.metric("Total Fair Value", f"${df['Fair Value'].sum():,.2f}")
    st.metric("Portfolio MOIC", f"{(df['Fair Value'].sum() / df['Cost'].sum()):.2f}")
    st.metric("Estimated IRR", irr_display)

    st.subheader("MOIC by Investment")
    st.dataframe(df[["Investment Name", "Cost", "Fair Value", "MOIC"]].sort_values("MOIC", ascending=False))
