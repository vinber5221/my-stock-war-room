import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="AI 股票完全體-全情報版", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【數據引擎：證交所直連】 ---
@st.cache_data(ttl=3600)
def get_twse_data():
    try:
        p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10).json()
        c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10).json()
        p_df, c_df = pd.DataFrame(p_res), pd.DataFrame(c_res)
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged
    except: return None

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.metric("💰 帳戶餘額", f"${st.session_state.balance:,.0f}")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    st.divider()
    if st.button("♻️ 強制重整數據"):
        st.cache_data.clear()
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 100萬實戰：全情報戰情室")

all_data = get_twse_data()

if all_data is not None:
    # 第一層：籌碼鎖碼雷達
    with st.expander("🚀 今日法人同步鎖碼名單", expanded=False):
        radar = all_data[(all_data['ForeignInvestorBuySellDiff'] > 0) & 
                         (all_data['InvestmentTrustBuySellDiff'] > 0) & 
                         (all_data['ChangePct'] >= 2.0)].sort_values(by='ChangePct', ascending=False)
        st.dataframe(radar[['Code', 'Name', 'ClosingPrice', 'ChangePct', 'ForeignInvestorBuySellDiff']].head(10), hide_index=True)

    st.divider()

    # 第二層：個股情報 (EPS, ROE, 毛利)
    symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
    stock_tool = yf.Ticker(symbol)
    
    # 抓取 K 線數據
    hist = yf.download(symbol, period="1d", interval="5m", timeout=5)
    
    if not hist.empty:
        cur_p = float(hist['Close'].iloc[-1])
        
        # 顯示財報數據
        try:
            info = stock_tool.info
            st.subheader(f"📊 {info.get('shortName', target_code)} 關鍵情報")
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("當前股價", f"{cur_p:.2f}")
            i2.metric("🧬 EPS", f"{info.get('trailingEps', 'N/A')}")
            i3.metric("💰 毛利率", f"{info.get('grossMargins', 0)*100:.2f}%")
            i4.metric("📈 ROE (投報率)", f"{info.get('returnOnEquity', 0)*100:.2f}%")
        except:
            st.warning("基本面情報讀取中...")

        # 第三層：交易執行
        st.write("---")
        t1, t2, t3 = st.columns([1, 1, 2])
        with t1:
            if st.button(f"🔴 買進 1 張", use_container_width=True):
                st.session_state.balance -= cur_p * 1000
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.rerun()
        with t2:
            if st.button("🟢 全數賣出", use_container_width=True):
                st.session_state.balance += (cur_p * st.session_state.position * 1000)
                st.session_state.position = 0; st.session_state.buy_price = 0.0
                st.rerun()
        with t3:
            unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
            st.metric("持倉損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)

        # 第四層：K 線圖
        fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="成本線")
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("找不到該代碼行情，請確認輸入是否正確。")
