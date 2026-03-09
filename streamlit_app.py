import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="爸爸的實戰戰情室", layout="centered")

# 美化樣式
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; border-radius: 12px; background: #00ffc8; color: black; font-weight: bold; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ 100萬實戰-終極出水版")

# 2. 籌碼掃描功能 (原本的功能)
@st.cache_data(ttl=3600)
def fetch_chip_data():
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
        return merged[(merged['ForeignInvestorBuySellDiff'] > 0) & (merged['InvestmentTrustBuySellDiff'] > 0) & (merged['ChangePct'] >= 2.0)]
    except: return None

if st.button("🚀 執行法人鎖碼掃描"):
    df = fetch_chip_data()
    if df is not None and not df.empty:
        st.success(f"🎯 發現 {len(df)} 檔出水標的")
        for _, row in df.head(10).iterrows():
            with st.container(border=True):
                st.subheader(f"{row['Code']} {row['Name']}")
                st.write(f"📈 漲幅：{row['ChangePct']:.2f}% | 成交價：{row['ClosingPrice']}")
    else: st.warning("目前無符合條件標的...")

# 3. 新功能：實時 K 線圖
st.divider()
st.subheader("📈 個股實時走勢 (K線)")
target = st.text_input("輸入股票代碼 (如: 2330 或 ^TWII)", value="2330")

if target:
    with st.spinner("正在讀取行情資料..."):
        symbol = "^TWII" if target == "^TWII" else f"{target}.TW"
        # 抓取 5 分鐘 K 線
        data = yf.download(symbol, period="1d", interval="5m")
        if not data.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'],
                low=data['Low'], close=data['Close'], name='K線')])
            fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=400, margin=dict(l=5, r=5, t=10, b=5))
            st.plotly_chart(fig, use_container_width=True)
            
            curr = data['Close'].iloc[-1].values[0] if hasattr(data['Close'].iloc[-1], 'values') else data['Close'].iloc[-1]
            st.metric(f"{target} 當前報價", f"{curr:.2f}")
        else: st.error("找不到數據，請確認代碼是否正確。")
