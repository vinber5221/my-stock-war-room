import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="100萬實戰-終極修復版", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    time_frame = st.radio("選擇週期", ('日 (近1年)', '週 (近2年)', '月 (近5年)'))
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 持倉數量: {st.session_state.position} 張")
    if st.button("🗑️ 重置帳戶"):
        st.session_state.balance = 1000000.0
        st.session_state.position = 0
        st.session_state.buy_price = 0.0
        st.rerun()

# --- 【數據抓取】 ---
symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
period_map = {'日 (近1年)': '1y', '週 (近2年)': '2y', '月 (近5年)': '5y'}
interval_map = {'日 (近1年)': '1d', '週 (近2年)': '1wk', '月 (近5年)': '1mo'}

try:
    df = yf.download(symbol, period=period_map[time_frame], interval=interval_map[time_frame], auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    if not df.empty:
        cur_p = round(float(df['Close'].iloc[-1]), 2)
        
        # --- A. 頂部情報看板 ---
        st.title(f"🛡️ {target_code} 實戰戰情室")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("當前成交價", f"{cur_p:,.2f}")
        
        # 財報抓取 (加入防撞機制)
        eps, gross, roe = "讀取中", "讀取中", "讀取中"
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            if isinstance(info, dict):
                eps = info.get('trailingEps', 'N/A')
                gross = f"{info.get('grossMargins', 0)*100:.1f}%"
                roe = f"{info.get('returnOnEquity', 0)*100:.1f}%"
        except:
            pass # 即使失敗也不要報錯
            
        c2.metric("🧬 EPS", eps)
        c3.metric("💰 毛利率", gross)
        c4.metric("📈 ROE", roe)

        # --- B. 模擬交易與損益 (確保按鈕一定會出來) ---
        st.write("---")
        st.subheader("⚔️ 模擬實戰執行")
        t1, t2, t3 = st.columns([1, 1, 2])
        
        with t1:
            if st.button(f"🔴 買進 1 張", use_container_width=True):
                if st.session_state.balance >= cur_p * 1000:
                    st.session_state.balance -= cur_p * 1000
                    st.session_state.position += 1
                    st.session_state.buy_price = cur_p
                    st.rerun()
        
        with t2:
            if st.button("🟢 全數賣出", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.position = 0; st.session_state.buy_price = 0.0
                    st.rerun()
        
        with t3:
            if st.session_state.position > 0:
                diff = cur_p - st.session_state.buy_price
                unrealized = diff * st.session_state.position * 1000
                roi_val = (diff / st.session_state.buy_price) * 100 if st.session_state.buy_price > 0 else 0
                st.metric("持倉帳面損益", f"{unrealized:,.0f}", delta=f"{roi_val:.2f}%")
            else:
                st.metric("持倉帳面損益", "無持股", delta=None)

        # --- C. 伸縮 K 線圖 ---
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="你的成本")
        
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("找不到行情數據")

except Exception as e:
    st.info("系統校準中... 請稍候")
