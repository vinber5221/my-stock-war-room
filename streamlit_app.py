import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

# 1. 頁面配置
st.set_page_config(page_title="證交所直連-實戰戰情室", layout="wide", initial_sidebar_state="expanded")

# 初始化帳戶 (100萬實戰)
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【核心數據引擎：直連證交所】 ---
@st.cache_data(ttl=3600)
def get_twse_data():
    try:
        # 抓取全市場行情
        p_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        p_res = requests.get(p_url, timeout=15)
        p_df = pd.DataFrame(p_res.json())
        
        # 抓取三大法人買賣超
        c_url = "https://openapi.twse.com.tw/v1/fund/T86_ALL"
        c_res = requests.get(c_url, timeout=15)
        c_df = pd.DataFrame(c_res.json())
        
        # 數據清洗：將字串轉為數字
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change', 'Diff', 'Volume']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 合併數據
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        # 計算漲跌幅
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged
    except Exception as e:
        st.error(f"證交所連線異常: {e}")
        return None

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.write(f"💰 剩餘現金: ${st.session_state.balance:,.0f}")
    st.divider()
    if st.button("🔄 刷新證交所數據"):
        st.cache_data.clear()
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 證交所 API 直連實戰版")

all_data = get_twse_data()

if all_data is not None:
    # 第一層：籌碼雷達 (法人鎖碼)
    st.subheader("🚀 今日法人鎖碼雷達 (外資+投信雙增)")
    # 篩選條件：外資買超 > 0 且 投信買超 > 0 且 漲幅 > 2%
    radar_df = all_data[
        (all_data['ForeignInvestorBuySellDiff'] > 0) & 
        (all_data['InvestmentTrustBuySellDiff'] > 0) & 
        (all_data['ChangePct'] >= 2.0)
    ].sort_values(by='ChangePct', ascending=False)
    
    st.dataframe(radar_df[['Code', 'Name', 'ClosingPrice', 'ChangePct', 'ForeignInvestorBuySellDiff', 'InvestmentTrustBuySellDiff']].head(10), hide_index=True)

    st.divider()

    # 第二層：個股情報與交易
    st.subheader("⚔️ 個股實戰演練")
    target_code = st.text_input("輸入要查看的代碼", value="2330")
    
    # 從證交所資料庫抓取該股當天資訊
    stock_info = all_data[all_data['Code'] == target_code]
    
    if not stock_info.empty:
        row = stock_info.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("今日收盤", f"{row['ClosingPrice']}")
        c2.metric("今日漲跌", f"{row['Change']}", f"{row['ChangePct']:.2f}%")
        c3.metric("外資買賣", f"{int(row['ForeignInvestorBuySellDiff']/1000)}張")
        c4.metric("投信買賣", f"{int(row['InvestmentTrustBuySellDiff']/1000)}張")

        # 簡單的模擬買賣邏輯
        if st.button(f"🔴 模擬以 {row['ClosingPrice']} 買進 1 張"):
            cost = row['ClosingPrice'] * 1000
            if st.session_state.balance >= cost:
                st.session_state.balance -= cost
                st.session_state.trade_log.append({
                    "時間": datetime.now().strftime("%H:%M:%S"),
                    "代碼": target_code,
                    "價格": row['ClosingPrice'],
                    "動作": "買進"
                })
                st.success(f"已成交！剩餘現金: ${st.session_state.balance:,.0f}")
            else:
                st.error("現金不足！")
    else:
        st.warning("請輸入正確的四位數股票代碼。")

# 交易日誌
if st.session_state.trade_log:
    with st.expander("📋 查看今日交易日誌"):
        st.table(pd.DataFrame(st.session_state.trade_log))
