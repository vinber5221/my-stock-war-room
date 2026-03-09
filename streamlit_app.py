import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import urllib3
from datetime import datetime

# 1. 基礎設定
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="100萬實戰-價格終極修正版", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶
for key, val in {'balance': 1000000.0, 'position': 0, 'buy_price': 0.0}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    target_code = st.text_input("🔍 代碼演練", value="2330").strip()
    st.divider()
    if st.button("♻️ 徹底重新整理"): st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 100萬實戰：行情修復戰情室")

symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"

with st.spinner('數據精準校正中...'):
    try:
        # 強制關閉 auto_adjust 並攤平數據
        df = yf.download(symbol, period="5d", interval="5m", auto_adjust=False, progress=False)
        
        # 關鍵修復：處理多重索引，確保只取 Close, Open, High, Low
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 修正價格：如果是台股且價格異常，取 'Close' 欄位的第一列
        if not df.empty:
            # 確保取到的是單一數值
            latest_data = df.iloc[-1]
            cur_p = float(latest_data['Close'])
            
            # --- 情報看板 ---
            st.subheader(f"📊 {target_code} 即時報價看板")
            c1, c2, c3 = st.columns(3)
            c1.metric("當前股價", f"{cur_p:.2f}")
            
            # 基本面 (EPS/ROE)
            try:
                t = yf.Ticker(symbol)
                info = t.info
                c2.metric("🧬 EPS", f"{info.get('trailingEps', 'N/A')}")
                c3.metric("💰 毛利率", f"{info.get('grossMargins', 0)*100:.1f}%")
            except:
                c2.write("基本面資訊同步中...")

            # --- 交易與損益 ---
            st.divider()
            t1, t2, t3 = st.columns([1, 1, 2])
            with t1:
                if st.button("🔴 買進 1 張", use_container_width=True):
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
                p_l = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
                st.metric("持倉損益", f"{p_l:,.0f}", delta=f"{(p_l/1000000)*100:.2f}%" if st.session_state.position > 0 else None)

            # --- K 線圖繪製 (修復視覺斷層) ---
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='K線'
            )])
            if st.session_state.position > 0:
                fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red")
            
            fig.update_layout(
                height=550, template="plotly_dark", 
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis_title="價格 (TWD)"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error("❌ 找不到數據，請確認代碼（如：2330）。")
            
    except Exception as e:
        st.error(f"📡 系統校準中，請稍候再試。")
