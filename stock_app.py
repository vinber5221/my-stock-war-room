import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import time

# 1. 頁面配置
st.set_page_config(page_title="100萬實戰-秒開版", layout="wide")

# 初始化帳戶 (確保狀態在刷新時不會消失)
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【數據抓取：快取模式避免卡頓】 ---
@st.cache_data(ttl=60) # 60秒內不用重複抓取
def get_stock_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    time_frame = st.radio("選擇週期", ('1y', '2y', '5y'), format_func=lambda x: {'1y':'日', '2y':'週', '5y':'月'}[x])
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 目前持倉: {st.session_state.position} 張")
    if st.button("🗑️ 帳戶重置"):
        st.session_state.balance = 1000000.0
        st.session_state.position = 0
        st.session_state.buy_price = 0.0
        st.rerun()

# --- 【核心邏輯】 ---
symbol = f"{target_code}.TW"
interval = '1d' if time_frame == '1y' else ('1wk' if time_frame == '2y' else '1mo')

try:
    df = get_stock_data(symbol, time_frame, interval)
    
    if not df.empty:
        cur_p = round(float(df['Close'].iloc[-1]), 2)
        
        st.title(f"🛡️ {target_code} 實戰戰情室")
        
        # 數據看板
        c1, c2, c3 = st.columns(3)
        c1.metric("當前成交價", f"{cur_p:,.2f}")
        
        # 損益計算
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        roi = ((cur_p - st.session_state.buy_price) / st.session_state.buy_price * 100) if st.session_state.position > 0 else 0
        c2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{roi:.2f}%" if st.session_state.position > 0 else None)
        c3.metric("平均成本", f"{st.session_state.buy_price:,.2f}")

        # --- 模擬交易按鈕 (加上 Key 確保點擊有效) ---
        st.divider()
        b1, b2 = st.columns(2)
        
        with b1:
            if st.button(f"🔴 買進 1 張 (${cur_p})", key="buy_btn", use_container_width=True):
                if st.session_state.balance >= cur_p * 1000:
                    st.session_state.balance -= cur_p * 1000
                    st.session_state.position += 1
                    st.session_state.buy_price = cur_p
                    st.rerun() # 強制刷新顯示結果
        
        with b2:
            if st.button("🟢 全數賣出", key="sell_btn", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.position = 0
                    st.session_state.buy_price = 0.0
                    st.rerun()

        # K 線圖
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="你的成本")
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True)
        st.plotly_chart(fig, use_container_width=True)

except:
    st.info("衛星通訊連線中...")
