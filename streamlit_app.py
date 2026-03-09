import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 1. 頁面配置
st.set_page_config(page_title="100萬實戰-流暢校正版", layout="wide")

# 2. 帳戶狀態初始化 (確保這些數據永遠不會因為刷新而消失)
for key, val in {'balance': 1000000.0, 'position': 0, 'buy_price': 0.0}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 【數據抓取函數：加入快取保護避免卡頓】 ---
@st.cache_data(ttl=60)
def get_clean_data(symbol, tf):
    p_map = {'1y': '1y', '2y': '2y', '5y': '5y'}
    i_map = {'1y': '1d', '2y': '1wk', '5y': '1mo'}
    # 下載數據，強制 auto_adjust 為 False 以獲得原始價格
    df = yf.download(symbol, period=p_map[tf], interval=i_map[tf], auto_adjust=False, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    time_frame = st.radio("選擇週期", ('1y', '2y', '5y'), format_func=lambda x: {'1y':'日K', '2y':'週K', '5y':'月K'}[x])
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 目前持倉: {st.session_state.position} 張")
    if st.button("🗑️ 重置帳戶狀態"):
        for k in ['balance', 'position', 'buy_price']: st.session_state[k] = (1000000.0 if k=='balance' else 0)
        st.rerun()

# --- 【主畫面與交易邏輯】 ---
symbol = f"{target_code}.TW"

# A. 先抓取數據，如果卡住會顯示轉圈圖示
with st.spinner("同步數據中..."):
    df = get_clean_data(symbol, time_frame)

if not df.empty:
    cur_p = round(float(df['Close'].iloc[-1]), 2)
    st.title(f"📊 {target_code} 實戰戰情室")

    # B. 數據看板
    c1, c2, c3 = st.columns(3)
    c1.metric("當前成交價", f"{cur_p:,.2f}")
    
    # 計算即時損益
    if st.session_state.position > 0:
        p_l = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000
        roi = (cur_p - st.session_state.buy_price) / st.session_state.buy_price * 100
        c2.metric("帳面損益", f"{p_l:,.0f}", delta=f"{roi:.2f}%")
        c3.metric("持倉成本", f"{st.session_state.buy_price:,.2f}")
    else:
        c2.metric("帳面損益", "無持股")
        c3.metric("平均成本", "0.00")

    # C. 模擬交易區 (把邏輯直接寫在按鈕內，確保響應)
    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button(f"🔴 買進 1 張 (${cur_p})", use_container_width=True):
            if st.session_state.balance >= cur_p * 1000:
                st.session_state.balance -= cur_p * 1000
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.rerun()
    with b2:
        if st.button("🟢 全數賣出平倉", use_container_width=True):
            if st.session_state.position > 0:
                st.session_state.balance += (cur_p * st.session_state.position * 1000)
                st.session_state.position = 0
                st.session_state.buy_price = 0.0
                st.rerun()

    # D. K 線圖繪製 (優化比例與伸縮)
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], name='K線'
    )])
    
    if st.session_state.position > 0:
        fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="你的成本線")

    fig.update_layout(
        height=550, template="plotly_dark", 
        xaxis_rangeslider_visible=True,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="價格 (TWD)"
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("暫時無法取得數據，請確認台股代碼後再重試。")
