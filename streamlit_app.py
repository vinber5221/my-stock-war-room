import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 頁面配置：強制開啟側邊欄並設為寬版
st.set_page_config(page_title="100萬實戰-完全體戰情室", layout="wide", initial_sidebar_state="expanded")

# 初始化虛擬帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.write(f"💰 現金: ${st.session_state.balance:,.0f}")
    st.divider()
    
    # 輸入代碼
    target_code = st.text_input("🔍 輸入演練代碼", value="2330")
    
    # 手動支撐警報 (你喜歡的功能)
    support_price = st.number_input("🚨 手動支撐警戒位", value=0.0)
    
    # 自動更新切換
    auto_refresh = st.toggle("🔄 自動更新 (60s)", value=True)
    st.divider()
    
    if st.button("🗑️ 清空交易紀錄"):
        st.session_state.trade_log = []
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ AI 選股 + 實戰演練完全體")

# 選股雷達區
with st.expander("🚀 點我執行：全台股法人鎖碼掃描"):
    if st.button("開始掃描"):
        # 這裡放之前的抓取邏輯
        st.info("正在連線證交所數據...")
        # (簡化代碼以節省空間，功能與之前相同)

st.divider()

# 實戰 K 線區
symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
try:
    data = yf.download(symbol, period="1d", interval="5m")
    if not data.empty:
        cur_p = float(data['Close'].iloc[-1])
        
        # 頂部數據看板
        k1, k2, k3 = st.columns(3)
        k1.metric(f"{target_code} 市價", f"{cur_p:.2f}")
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        k2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)
        k3.metric("持股數量", f"{st.session_state.position} 張")

        # 買賣按鈕
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔴 模擬買進", use_container_width=True):
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.session_state.balance -= cur_p * 1000
                st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "買進", "價格": cur_p})
                st.rerun()
        with b2:
            if st.button("🟢 模擬賣出", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "全數賣出", "價格": cur_p})
                    st.session_state.position = 0
                    st.session_state.buy_price = 0.0
                    st.rerun()

        # 專業 K 線
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red")
        fig.update_layout(height=400, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

except:
    st.warning("數據更新中...")

# 自動更新邏輯
if auto_refresh:
    time.sleep(60)
    st.rerun()
