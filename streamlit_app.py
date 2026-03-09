import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="爸爸的實戰戰情室", layout="centered")

@st.cache_data(ttl=3600)
def fetch_data():
    try:
        p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10)
        c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10)
        p_df = pd.DataFrame(p_res.json())
        c_df = pd.DataFrame(c_res.json())
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged[(merged['ForeignInvestorBuySellDiff'] > 0) & (merged['InvestmentTrustBuySellDiff'] > 0) & (merged['ChangePct'] >= 2.0)]
    except: return None

st.title("🛡️ 100萬實戰-終極出水版")
if st.button("🚀 執行法人鎖碼掃描", use_container_width=True):
    df = fetch_data()
    if df is not None and not df.empty:
        st.success(f"發現 {len(df)} 檔出水標的")
        st.dataframe(df[['Code', 'Name', 'ClosingPrice', 'ChangePct']], hide_index=True)
    else: st.warning("目前無符合條件標的...")
