import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time

# 1. 頁面配置與導航
st.set_page_config(page_title="100萬實戰-完全體戰情室", layout="wide")

# 初始化虛擬帳戶 (只在第一次啟動時執行)
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'position' not in st.session_state: st.session_state.position = 0
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_log' not in st.session_state: st.session_state.trade_log = []

# --- 第一部分：法人鎖碼選股雷達 ---
st.title("🛡️ AI 籌碼選股雷達 (盤後掃描)")

@st.cache_data(ttl=3600)
def fetch_chip_data():
    try:
        p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=10).json()
        c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=10).json()
        p_df, c_df = pd.DataFrame(p_res), pd.DataFrame(c_res)
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        # 篩選：外資買+投信買+漲幅>2%
        return merged[(merged['ForeignInvestorBuySellDiff'] > 0) & (merged['InvestmentTrustBuySellDiff'] > 0) & (merged['ChangePct'] >= 2.0)]
    except: return None

if st.button("🚀 執行全台股法人鎖碼掃描"):
    df = fetch_chip_data()
    if df is not None and not df.empty:
        st.success(f"🎯 發現 {len(df)} 檔符合標的")
        st.dataframe(df[['Code', 'Name', 'ClosingPrice', 'ChangePct']].head(10), hide_index=True)
    else: st.warning("目前市場較觀望，尚無符合標的。")

st.divider()

# --- 第二部分：實時 K 線與模擬交易 ---
st.header("⚔️ 個股實戰演練 (K線走勢)")

# 側邊欄控制
st.sidebar.header("🕹️ 操作面板")
target_code = st.sidebar.text_input("輸入要演練的代碼", value="2330")
symbol = f"{target_code}.TW" if target_code != "^TWII" else "^TWII"

try:
    # 抓取 5 分鐘數據畫 K 線
    data = yf.download(symbol, period="1d", interval="5m")
    if not data.empty:
        cur_p = float(data['Close'].iloc[-1])
        
        # 數據看板
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{target_code} 當前市價", f"{cur_p:.2f}")
        unrealized = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000 if st.session_state.position > 0 else 0
        c2.metric("帳面損益", f"{unrealized:,.0f}", delta=f"{(unrealized/1000000)*100:.2f}%" if unrealized != 0 else None)
        c3.metric("剩餘現金", f"{st.session_state.balance:,.0f}")

        # 交易按鈕
        bt1, bt2 = st.columns(2)
        with bt1:
            if st.button("🔴 模擬買進 1 張 (1000股)", use_container_width=True):
                if st.session_state.balance >= cur_p * 1000:
                    st.session_state.position += 1
                    st.session_state.buy_price = cur_p
                    st.session_state.balance -= cur_p * 1000
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M:%S"), "代碼": target_code, "動作": "買進", "價格": cur_p})
                    st.rerun()
        with bt2:
            if st.button("🟢 模擬全數平倉 (賣出)", use_container_width=True):
                if st.session_state.position > 0:
                    profit = (cur_p - st.session_state.buy_price) * st.session_state.position * 1000
                    st.session_state.balance += (cur_p * st.session_state.position * 1000)
                    st.session_state.trade_log.append({"時間": datetime.now().strftime("%H:%M:%S"), "代碼": target_code, "動作": "平倉", "價格": cur_p, "損益": profit})
                    st.session_state.position = 0
                    st.session_state.buy_price = 0.0
                    st.rerun()

        # 繪製 K 線圖
        fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name='K線')])
        if st.session_state.position > 0:
            fig.add_hline(y=st.session_state.buy_price, line_dash="dash", line_color="red", annotation_text="買進成本線")
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=5, r=5, t=10, b=5))
        st.plotly_chart(fig, use_container_width=True)

        # 交易紀錄
        if st.session_state.trade_log:
            st.subheader("📋 今日模擬交易紀錄")
            st.table(pd.DataFrame(st.session_state.trade_log).tail(5))
            
    else: st.error("找不到個股數據，請檢查代碼。")
except Exception as e:
    st.info("等待數據讀取中...")

# 自動刷新開關
if st.sidebar.toggle("自動更新行情 (60s)", value=True):
    time.sleep(60)
    st.rerun()
