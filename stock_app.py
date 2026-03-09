import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="100萬實戰-情報武裝版", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 輸入台股代碼", value="2330").strip()
    
    time_frame = st.radio(
        "選擇查看週期",
        ('日 (近1年)', '週 (近2年)', '月 (近5年)', '年 (全部)'),
        index=0
    )
    
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 目前持倉: {st.session_state.position} 張")
    
    if st.button("♻️ 徹底刷新數據"):
        st.rerun()

# --- 【數據處理與情報抓取】 ---
period_map = {'日 (近1年)': '1y', '週 (近2年)': '2y', '月 (近5年)': '5y', '年 (全部)': 'max'}
interval_map = {'日 (近1年)': '1d', '週 (近2年)': '1wk', '月 (近5年)': '1mo', '年 (全部)': '1mo'}

symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
stock_tool = yf.Ticker(symbol)

try:
    # 抓取 K 線行情
    df = yf.download(symbol, period=period_map[time_frame], interval=interval_map[time_frame], auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if not df.empty:
        cur_p = round(float(df['Close'].iloc[-1]), 2)
        
        # --- 1. 頂部情報看板 (EPS, 毛利, ROE) ---
        st.title(f"🛡️ {target_code} 情報戰情室")
        i1, i2, i3, i4 = st.columns(4)
        
        # 抓取財務數據 (利用 try 避免單項數據缺失導致崩潰)
        try:
            info = stock_tool.info
            eps = info.get('trailingEps', 'N/A')
            gross_margin = info.get('grossMargins', 0) * 100
            roe = info.get('returnOnEquity', 0) * 100
            i1.metric("當前成交價", f"{cur_p:,.2f}")
            i2.metric("🧬 EPS (獲利力)", f"{eps}")
            i3.metric("💰 毛利率", f"{gross_margin:.1f}%")
            i4.metric("📈 ROE (投報率)", f"{roe:.1f}%")
        except:
            i1.metric("當前成交價", f"{cur_p:,.2f}")
            st.warning("基本面情報同步中，請稍候...")

        # --- 2. 模擬實戰交易區 ---
        st.write("---")
        t1, t2, t3 = st.columns([1, 1, 2])
        
        with t1:
            if st.button(f"🔴 模擬買進 1 張 (${cur_p})", use_container_width=True):
                if st.session_state.balance >= cur_p * 1000:
                    st.session_state.balance -= cur_p * 1000
                    st.session_state.position += 1
                    st.session_state.buy_price = cur_p
                    st.rerun()
                else:
                    st.error("資金不足！")
                    
        with t2:
            if st.button("🟢 模擬全數平倉", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.position = 0; st.session_state.buy_price = 0.0
                    st.rerun()
        
        with t3:
            unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
            st.metric("持倉帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if st.session_state.position > 0 else None)

        # --- 3. 專業 K 線伸縮圖 ---
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="成本線")
        
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=True, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"數據加載中，請確保代碼正確並稍候...")
