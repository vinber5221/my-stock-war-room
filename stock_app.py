import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="100萬實戰-階段一", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    target_code = st.text_input("🔍 輸入台股代碼", value="2330").strip()
    
    # K線週期切換：這就是你要求的年、月、週、日
    time_frame = st.radio(
        "選擇查看週期",
        ('日 (近1年)', '週 (近2年)', '月 (近5年)', '年 (全部)'),
        index=0
    )
    
    st.divider()
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.write(f"💼 持倉數量: {st.session_state.position} 張")
    
    if st.button("♻️ 刷新數據"):
        st.rerun()

# --- 【數據抓取邏輯】 ---
# 根據按鈕選擇，決定 yfinance 抓取的時間範圍
period_map = {
    '日 (近1年)': '1y',
    '週 (近2年)': '2y',
    '月 (近5年)': '5y',
    '年 (全部)': 'max'
}
interval_map = {
    '日 (近1年)': '1d',
    '週 (近2年)': '1wk',
    '月 (近5年)': '1mo',
    '年 (全部)': '1mo' # yfinance '年'單位通常以月K呈現較清楚
}

symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"

try:
    # 抓取數據 (使用 auto_adjust=False 確保價格真實，不被除權息干擾)
    df = yf.download(symbol, period=period_map[time_frame], interval=interval_map[time_frame], auto_adjust=False)
    
    # 強制攤平索引，防止抓錯價格
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if not df.empty:
        cur_p = round(float(df['Close'].iloc[-1]), 2)
        
        # --- 上方實時數據看板 ---
        st.title(f"📊 {target_code} 實戰看板 ({time_frame})")
        
        # 這裡預留位置，下一階段我們會加入 EPS, ROE
        c1, c2, c3 = st.columns(3)
        c1.metric("當前成交價", f"{cur_p:,.2f}")
        
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        c2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if st.session_state.position > 0 else None)
        c3.metric("平均成本", f"{st.session_state.buy_price:,.2f}")

        # --- 專業 K 線圖 (具備縮放功能) ---
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='K線'
        )])
        
        # 繪製成本線
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="我的成本")

        # 圖表設定：加入伸縮滑桿 (Range Slider)
        fig.update_layout(
            height=600,
            template="plotly_dark",
            xaxis_rangeslider_visible=True, # 底部的伸縮滑桿
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="價格 (TWD)"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("❌ 找不到代碼數據，請確認輸入正確（例如：2330）。")

except Exception as e:
    st.error(f"系統啟動中... 請稍候。")
