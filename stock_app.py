import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 頁面配置：強制開啟側邊欄
st.set_page_config(page_title="100萬實戰-終極戰情室", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.metric("💰 帳戶餘額", f"${st.session_state.balance:,.0f}")
    target_code = st.text_input("🔍 輸入股票代碼", value="2330").strip()
    st.divider()
    auto_refresh = st.toggle("🔄 自動更新 (60s)", value=False)
    if st.button("♻️ 強制重整頁面"):
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 100萬實戰：全情報戰情室")

symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
stock_tool = yf.Ticker(symbol)

try:
    # 優先抓取行情 (確保圖表先出來)
    with st.spinner('正在同步即時行情...'):
        hist = yf.download(symbol, period="5d", interval="5m", timeout=10)
    
    if not hist.empty:
        cur_p = float(hist['Close'].iloc[-1])
        
        # --- 第一層：基本面情報 (EPS, 毛利, ROE) ---
        # 這裡用 Try 鎖定，不讓財報抓取卡住 K 線
        st.subheader(f"📊 {target_code} 關鍵財務情報")
        inf1, inf2, inf3, inf4 = st.columns(4)
        
        try:
            info = stock_tool.info
            inf1.metric("當前股價", f"{cur_p:.2f}")
            inf2.metric("🧬 EPS", f"{info.get('trailingEps', 'N/A')}")
            inf3.metric("💰 毛利率", f"{info.get('grossMargins', 0)*100:.2f}%")
            inf4.metric("📈 ROE (投報率)", f"{info.get('returnOnEquity', 0)*100:.2f}%")
        except:
            inf1.metric("當前股價", f"{cur_p:.2f}")
            inf2.write("財報數據讀取中...")

        # --- 第二層：模擬交易與損益 ---
        st.divider()
        t1, t2, t3 = st.columns([1, 1, 2])
        with t1:
            if st.button(f"🔴 模擬買進 1 張", use_container_width=True):
                st.session_state.balance -= cur_p * 1000
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.rerun()
        with t2:
            if st.button("🟢 全數賣出平倉", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.position = 0; st.session_state.buy_price = 0.0
                    st.rerun()
        with t3:
            unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
            st.metric("目前持倉損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)

        # --- 第三層：專業 K 線圖 ---
        fig = go.Figure(data=[go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'],
            low=hist['Low'], close=hist['Close'], name='5分K'
        )])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="你的成本")
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("暫時無法取得該個股行情，請稍後重試。")

except Exception as e:
    st.error(f"系統整備中，請嘗試輸入其他代碼。")

if auto_refresh:
    time.sleep(60)
    st.rerun()
