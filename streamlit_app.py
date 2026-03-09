import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="證交所直連-實戰戰情室", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶 (100萬實戰)
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【數據引擎：直連證交所 OpenAPI】 ---
@st.cache_data(ttl=3600)
def get_twse_data():
    try:
        # 抓取全市場行情 (每日收盤價)
        p_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        # 抓取三大法人買賣超 (核心籌碼)
        c_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        
        p_res = requests.get(p_url, timeout=15).json()
        c_res = requests.get(c_url, timeout=15).json()
        
        p_df = pd.DataFrame(p_res)
        c_df = pd.DataFrame(c_res)
        
        # 數據清洗：字串轉數字並處理逗號
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change', 'Diff', 'Buy', 'Sell']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 合併行情與籌碼數據
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        # 計算漲跌幅 %
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged
    except Exception as e:
        st.error(f"證交所連線異常: {e}")
        return None

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.metric("💰 剩餘現金", f"${st.session_state.balance:,.0f}")
    st.divider()
    target_code = st.text_input("🔍 輸入演練代碼", value="2330")
    if st.button("🔄 刷新最新數據"):
        st.cache_data.clear()
        st.rerun()
    st.info("提示：數據每日 15:00 左右更新。")

# --- 【右側主畫面】 ---
st.title("🛡️ 100萬實戰：證交所直連版")

data_all = get_twse_data()

if data_all is not None:
    # 第一區：籌碼鎖碼雷達
    with st.expander("🚀 今日法人同步鎖碼名單 (漲幅 > 2% + 外資投信雙買)", expanded=True):
        radar_df = data_all[
            (data_all['ForeignInvestorBuySellDiff'] > 0) & 
            (data_all['InvestmentTrustBuySellDiff'] > 0) & 
            (data_all['ChangePct'] >= 2.0)
        ].sort_values(by='ChangePct', ascending=False)
        
        st.dataframe(radar_df[['Code', 'Name', 'ClosingPrice', 'ChangePct', 'ForeignInvestorBuySellDiff', 'InvestmentTrustBuySellDiff']].head(10), hide_index=True)

    st.divider()

    # 第二區：個股實戰演練
    st.subheader(f"⚔️ 個股即時情報：{target_code}")
    stock_info = data_all[data_all['Code'] == target_code]
    
    if not stock_info.empty:
        row = stock_info.iloc[0]
        
        # 情報看板
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("今日收盤價", f"{row['ClosingPrice']}")
        c2.metric("漲跌幅", f"{row['ChangePct']:.2f}%", delta=f"{row['Change']}")
        # 換算為張數 (原始單位為股)
        c3.metric("外資買賣 (張)", f"{int(row['ForeignInvestorBuySellDiff']/1000):,}")
        c4.metric("投信買賣 (張)", f"{int(row['InvestmentTrustBuySellDiff']/1000):,}")

        # 模擬交易區
        st.write("---")
        t1, t2, t3 = st.columns([1, 1, 2])
        cur_price = row['ClosingPrice']
        
        with t1:
            if st.button(f"🔴 買進 1 張 (${cur_price})", use_container_width=True):
                if st.session_state.balance >= cur_price * 1000:
                    st.session_state.balance -= cur_price * 1000
                    st.session_state.position += 1
                    st.session_state.buy_price = cur_price
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "買進", "價格": cur_price})
                    st.rerun()
        
        with t2:
            if st.button("🟢 全數平倉賣出", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_price * st.session_state.position * 1000)
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "賣出", "價格": cur_price})
                    st.session_state.position = 0; st.session_state.buy_price = 0.0
                    st.rerun()
        
        with t3:
            unrealized = (cur_price - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
            st.metric("持倉帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)

    else:
        st.warning("請在左側輸入正確的股票代碼。")

# 交易日誌
if st.session_state.trade_log:
    with st.expander("📋 今日模擬交易日誌"):
        st.table(pd.DataFrame(st.session_state.trade_log).tail(5))
