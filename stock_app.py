import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 1. 初始化 100 萬籌碼與交易紀錄
if 'balance' not in st.session_state:
    st.session_state.balance = 1000000.0  # 初始資金 100 萬
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}  # 持倉格式: {代號: {張數: n, 成本: p}}

# 2. 頁面設定
st.set_page_config(page_title="爸爸的 100 萬實戰選股器", layout="centered")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .status-card { background-color: #1e2130; padding: 20px; border-radius: 12px; border-left: 5px solid #00ffc8; margin-bottom: 20px; }
    .stock-card { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 3. 數據抓取引擎
@st.cache_data(ttl=1800)
def get_market_data():
    try:
        p_res = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", timeout=15)
        c_res = requests.get("https://openapi.twse.com.tw/v1/fund/T86_ALL", timeout=15)
        p_df, c_df = pd.DataFrame(p_res.json()), pd.DataFrame(c_res.json())
        for df in [p_df, c_df]:
            for col in df.columns:
                if any(k in col for k in ['Price', 'Change', 'Diff', 'Buy', 'Sell']):
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        merged = pd.merge(p_df, c_df, on='Code', suffixes=('', '_chip'))
        merged['ChangePct'] = (merged['Change'] / (merged['ClosingPrice'] - merged['Change'])) * 100
        return merged
    except:
        return None

# 4. 介面呈現：資產看板
st.title("🛡️ 100 萬模擬實戰戰情室")

with st.container():
    st.markdown(f"""
    <div class="status-card">
        <h3>💰 我的帳戶概況</h3>
        <p style='font-size: 1.2rem;'>可用現金：<b style='color:#00ffc8;'>${st.session_state.balance:,.0f}</b></p>
    </div>
    """, unsafe_allow_html=True)

# 顯示目前持倉
if st.session_state.portfolio:
    with st.expander("💼 查看我的持倉庫存", expanded=False):
        for code, info in st.session_state.portfolio.items():
            st.write(f"📈 **{code}** | 持有：{info['張數']} 張 | 平均成本：{info['成本']:.2f}")
            if st.button(f"賣出 {code}", key=f"sell_{code}"):
                # 簡單模擬賣出邏輯 (以最新價計算)
                st.session_state.balance += (info['成本'] * info['張數'] * 1000)
                del st.session_state.portfolio[code]
                st.rerun()

st.divider()

# 5. 掃描與交易邏輯
if st.button("🚀 執行全市場掃描 (尋找強勢股)"):
    with st.spinner("正在搜尋法人鎖碼標的..."):
        df = get_market_data()
        if df is None or df.empty:
            st.error("證交所連線忙碌中，請稍後再試。")
        else:
            targets = df[(df['ForeignInvestorBuySellDiff'] > 0) & 
                        (df['InvestmentTrustBuySellDiff'] > 0) & 
                        (df['ChangePct'] >= 2.0)].sort_values(by='ChangePct', ascending=False)

            if not targets.empty:
                st.success(f"🎯 找到 {len(targets)} 檔強勢候選股：")
                for _, row in targets.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="stock-card">
                            <h2 style='margin:0; color:#00ffc8;'>{row['Name']} ({row['Code']})</h2>
                            <p><b>現價：{row['ClosingPrice']}</b> | 漲幅：{row['ChangePct']:.2f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 買進按鈕
                        cost_per_lot = row['ClosingPrice'] * 1000
                        if st.button(f"🛒 模擬買進 1 張 (需 ${cost_per_lot:,.0f})", key=f"buy_{row['Code']}"):
                            if st.session_state.balance >= cost_per_lot:
                                st.session_state.balance -= cost_per_lot
                                code = f"{row['Name']}({row['Code']})"
                                if code in st.session_state.portfolio:
                                    st.session_state.portfolio[code]['張數'] += 1
                                else:
                                    st.session_state.portfolio[code] = {'張數': 1, '成本': row['ClosingPrice']}
                                st.toast(f"✅ 已買進 1 張 {row['Name']}", icon='💰')
                                st.rerun()
                            else:
                                st.error("❌ 現金不足！")
            else:
                st.warning("目前尚未找到符合條件的股票。")

st.caption("提示：點擊買進後，資產會自動扣除。下午 3 點後數據最準確。")