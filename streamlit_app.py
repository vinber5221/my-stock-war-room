import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 1. 頁面配置
st.set_page_config(page_title="爸爸的實戰戰情室", layout="wide")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【側邊欄：簡單控制】 ---
st.sidebar.header("🕹️ 指揮中心")
target = st.sidebar.text_input("輸入代碼 (如: 2330)", value="2330").strip()
if st.sidebar.button("♻️ 重新載入數據"):
    st.rerun()

st.sidebar.divider()
st.sidebar.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
st.sidebar.write(f"💼 持股: {st.session_state.position} 張")

# --- 【主畫面：行情與交易】 ---
st.title(f"📊 標的監控：{target}")

# 2. 抓取數據 (強制攤平格式)
symbol = f"{target}.TW" if target != "^TWII" else "^TWII"
df = yf.download(symbol, period="5d", interval="5m")

if not df.empty:
    # 這裡最關鍵：強制把多重索引攤平，只留我們需要的欄位
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 取得最新收盤價
    cur_p = round(float(df['Close'].iloc[-1]), 2)
    
    # 頂部看板
    c1, c2, c3 = st.columns(3)
    c1.metric("當前價格", f"{cur_p}")
    
    unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
    c2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if st.session_state.position > 0 else None)
    
    # 模擬交易按鈕
    st.write("---")
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
            st.session_state.buy_price = 0.0
            st.rerun()

    # 繪製 K 線圖 (回歸最穩定的設定)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='K線'
    )])
    
    fig.update_layout(
        height=500,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=10, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("找不到資料，請確認代碼是否輸入正確。")
