import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(page_title="100萬實戰-邏輯修正版", layout="wide", initial_sidebar_state="expanded")

# --- 【初始化與買賣邏輯處理】 ---
# 先處理買賣動作，確保後面的數據顯示是最新的
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    time_frame = st.radio("選擇週期", ('日 (近1年)', '週 (近2年)', '月 (近5年)', '年 (全部)'))
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 持倉數量: {st.session_state.position} 張")
    if st.button("♻️ 徹底刷新"): st.rerun()

# --- 【數據抓取與計算】 ---
symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
period_map = {'日 (近1年)': '1y', '週 (近2年)': '2y', '月 (近5年)': '5y', '年 (全部)': 'max'}
interval_map = {'日 (近1年)': '1d', '週 (近2年)': '1wk', '月 (近5年)': '1mo', '年 (全部)': '1mo'}

try:
    df = yf.download(symbol, period=period_map[time_frame], interval=interval_map[time_frame], auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    if not df.empty:
        cur_p = round(float(df['Close'].iloc[-1]), 2)
        
        # 1. 頂部情報看板
        st.title(f"🛡️ {target_code} 實戰戰情室")
        c1, c2, c3, c4 = st.columns(4)
        info = yf.Ticker(symbol).info
        c1.metric("當前成交價", f"{cur_p:,.2f}")
        c2.metric("🧬 EPS", f"{info.get('trailingEps', 'N/A')}")
        c3.metric("💰 毛利率", f"{info.get('grossMargins', 0)*100:.1f}%")
        c4.metric("📈 ROE", f"{info.get('returnOnEquity', 0)*100:.1f}%")

        # 2. 模擬交易執行 (移到看板下方，讓操作更直覺)
        st.write("---")
        t1, t2, t3 = st.columns([1, 1, 2])
        with t1:
            if st.button(f"🔴 買進 1 張", use_container_width=True):
                st.session_state.balance -= cur_p * 1000
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.rerun() # 買完立刻重整，損益才會跳
        with t2:
            if st.button("🟢 全數賣出", use_container_width=True):
                st.session_state.balance += (cur_p * st.session_state.position * 1000)
                st.session_state.position = 0; st.session_state.buy_price = 0.0
                st.rerun()
        with t3:
            # 這裡就是修正的地方：確保計算是用當前最新的持倉狀態
            p_l = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
            st.metric("當前持倉損益", f"{p_l:,.0f}", delta=f"{(p_l/1000000)*100:.2f}%" if st.session_state.position > 0 else None)

        # 3. K 線圖
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="成本線")
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

except:
    st.error("數據讀取中...")
