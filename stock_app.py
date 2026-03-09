import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="證交所官方直連戰情室", layout="wide")

# 初始化帳戶邏輯 (100萬實戰)
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0

# --- 【數據引擎：直連證交所 OpenAPI】 ---
@st.cache_data(ttl=60) # 每分鐘自動更新一次
def get_realtime_twse(code):
    try:
        # 直接抓取證交所全市場每日行情
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        res = requests.get(url, timeout=10)
        data = res.json()
        df = pd.DataFrame(data)
        
        # 篩選出爸爸要的這檔股票
        target_df = df[df['Code'] == code]
        
        if not target_df.empty:
            # 強制清洗數據，確保價格是真實數字 (去掉逗號)
            price = float(str(target_df.iloc[0]['ClosingPrice']).replace(',', ''))
            name = target_df.iloc[0]['Name']
            change = float(str(target_df.iloc[0]['Change']).replace(',', ''))
            return {"price": price, "name": name, "change": change}
        return None
    except:
        return None

# --- 【左側指揮中心】 ---
st.sidebar.header("🕹️ 指揮中心")
target_code = st.sidebar.text_input("輸入台股代碼", value="2330").strip()
st.sidebar.divider()
st.sidebar.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
st.sidebar.write(f"💼 目前持倉: {st.session_state.position} 張")

if st.sidebar.button("♻️ 刷新官方數據"):
    st.cache_data.clear()
    st.rerun()

# --- 【主畫面：官方真實行情】 ---
info = get_realtime_twse(target_code)

if info:
    st.title(f"🛡️ {info['name']} ({target_code}) 實戰監控")
    
    cur_p = info['price']
    
    # 看板：顯示最真實的收盤價
    c1, c2, c3 = st.columns(3)
    c1.metric("官方真實價格", f"{cur_p:,.2f}", delta=f"{info['change']}")
    
    # 計算損益
    unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
    c2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if st.session_state.position > 0 else None)
    c3.metric("持倉成本", f"{st.session_state.buy_price:,.2f}")

    # 模擬交易
    st.divider()
    b1, b2 = st.columns(2)
    with b1:
        if st.button(f"🔴 以 {cur_p} 買進 1 張 (1000股)", use_container_width=True):
            st.session_state.balance -= cur_p * 1000
            st.session_state.position += 1
            st.session_state.buy_price = cur_p
            st.rerun()
    with b2:
        if st.button("🟢 全數賣出平倉", use_container_width=True):
            st.session_state.balance += (cur_p * st.session_state.position * 1000)
            st.session_state.position = 0
            st.session_state.buy_price = 0.0
            st.rerun()

    # 備註說明
    st.caption("註：此數據直接連線台灣證交所 OpenAPI，反映當前最新官方收盤價格。")

else:
    st.error("❌ 找不到該代碼，或證交所 API 暫時繁忙。請確認代碼是否正確（如 2330）。")
