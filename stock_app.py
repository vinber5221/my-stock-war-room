import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="證交所直連-實戰戰情室", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【數據引擎：直連證交所 OpenAPI】 ---
@st.cache_data(ttl=3600)
def get_twse_data():
    try:
        # 抓取行情與籌碼 (TWSE OpenAPI)
        p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10).json()
        c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10).json()
        p_df, c_df = pd.DataFrame(p_res), pd.DataFrame(c_res)
        
        # 數值清洗
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change', 'Diff', 'Buy', 'Sell']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged
    except: return None

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    target_code = st.text_input("🔍 輸入演練代碼", value="2330")
    if st.button("🔄 刷新數據"):
        st.cache_data.clear()
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 100萬實戰：證交所直連版")
all_data = get_twse_data()

if all_data is not None:
    # 第一區：法人鎖碼雷達
    with st.expander("🚀 今日法人同步鎖碼名單", expanded=True):
        radar = all_data[(all_data['ForeignInvestorBuySellDiff'] > 0) & 
                         (all_data['InvestmentTrustBuySellDiff'] > 0) & 
                         (all_data['ChangePct'] >= 2.0)].sort_values(by='ChangePct', ascending=False)
        st.dataframe(radar[['Code', 'Name', 'ClosingPrice', 'ChangePct', 'ForeignInvestorBuySellDiff', 'InvestmentTrustBuySellDiff']].head(10), hide_index=True)

    # 第二區：實戰交易
    st.divider()
    stock = all_data[all_data['Code'] == target_code]
    if not stock.empty:
        row = stock.iloc[0]
        cur_p = row['ClosingPrice']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("今日收盤", f"{cur_p}")
        c2.metric("漲跌幅", f"{row['ChangePct']:.2f}%")
        c3.metric("外資買賣(張)", f"{int(row['ForeignInvestorBuySellDiff']/1000):,}")

        # 模擬下單
        b1, b2 = st.columns(2)
        with b1:
            if st.button(f"🔴 買進 1 張 (${cur_p})", use_container_width=True):
                st.session_state.balance -= cur_p * 1000
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.rerun()
        with b2:
            if st.button("🟢 全數賣出", use_container_width=True):
                st.session_state.balance += (cur_p * st.session_state.position * 1000)
                st.session_state.position = 0
                st.rerun()
        
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        st.metric("當前損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)
    else:
        st.warning("請輸入正確股票代碼")
