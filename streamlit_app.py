import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 頁面配置：強化側邊欄與寬版顯示
st.set_page_config(page_title="AI 股票完全體-財報情報版", layout="wide", initial_sidebar_state="expanded")

# 初始化虛擬帳戶
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 【左側指揮中心】 ---
with st.sidebar:
    st.header("🕹️ 指揮中心")
    st.write(f"💰 現金餘額: ${st.session_state.balance:,.0f}")
    st.divider()
    
    target_code = st.text_input("🔍 輸入監控代碼 (如: 2330)", value="2330")
    
    # 這裡加入一個自動更新開關，避免操作時網頁一直跳
    auto_refresh = st.toggle("🔄 自動更新行情 (60s)", value=True)
    
    st.divider()
    if st.button("🗑️ 重置所有交易"):
        st.session_state.balance = 1000000.0
        st.session_state.position = 0
        st.session_state.trade_log = []
        st.rerun()

# --- 【右側主畫面】 ---
st.title("🛡️ 實戰戰情室：基本面 + 籌碼 + K線")

# 第一層：法人鎖碼掃描 (收折式)
with st.expander("🚀 點我執行：今日法人同步鎖碼掃描 (盤後專用)"):
    if st.button("開始全市場掃描"):
        try:
            p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10).json()
            c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10).json()
            p_df, c_df = pd.DataFrame(p_res), pd.DataFrame(c_res)
            # 轉換數值
            for df in [p_df, c_df]:
                for col in df.columns:
                    if any(k in col for k in ['Price', 'Change']):
                        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
            merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
            merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
            result = merged[(merged['ForeignInvestorBuySellDiff'] > 0) & (merged['InvestmentTrustBuySellDiff'] > 0) & (merged['ChangePct'] >= 2.0)]
            st.dataframe(result[['Code', 'Name', 'ClosingPrice', 'ChangePct']].head(10), hide_index=True)
        except:
            st.error("證交所連線中，請稍候再試。")

st.divider()

# 第二層：個股情報與實戰演練
symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"
stock = yf.Ticker(symbol)

try:
    # 同步抓取行情與財報
    data = yf.download(symbol, period="1d", interval="5m")
    info = stock.info
    
    if not data.empty:
        cur_p = float(data['Close'].iloc[-1])
        
        # --- 核心情報看板 (爸爸最關心的數據) ---
        st.subheader(f"📊 {info.get('shortName', target_code)} 關鍵情報")
        inf1, inf2, inf3, inf4 = st.columns(4)
        
        # 抓取 EPS、毛利率、投報率 (ROE/ROA)
        eps = info.get('trailingEps', 'N/A')
        gross_margin = info.get('grossMargins', 0) * 100
        roe = info.get('returnOnEquity', 0) * 100
        
        inf1.metric("當前股價", f"{cur_p:.2f}")
        inf2.metric("🧬 EPS (每股盈餘)", f"{eps}")
        inf3.metric("💰 毛利率", f"{gross_margin:.2f}%")
        inf4.metric("📈 ROE (投報率)", f"{roe:.2f}%")

        # 損益看板
        st.write("---")
        p1, p2, p3 = st.columns(3)
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        p1.metric("帳面損益 (新台幣)", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)
        p2.metric("持股成本", f"{st.session_state.buy_price:.2f}")
        p3.metric("目前持倉", f"{st.session_state.position} 張")

        # 交易執行按鈕
        st.write("---")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔴 模擬買進 1 張", use_container_width=True):
                st.session_state.position += 1
                st.session_state.buy_price = cur_p
                st.session_state.balance -= cur_p * 1000
                st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "買進", "價格": cur_p})
                st.rerun()
        with b2:
            if st.button("🟢 模擬全數平倉", use_container_width=True):
                if st.session_state.position > 0:
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M"), "代碼": target_code, "動作": "賣出", "價格": cur_p})
                    st.session_state.position = 0
                    st.session_state.buy_price = 0.0
                    st.rerun()

        # 專業 K 線圖
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="你的成本線")
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

except:
    st.info("正在準備個股情報與 K 線數據...")

# 自動更新
if auto_refresh:
    time.sleep(60)
    st.rerun()
