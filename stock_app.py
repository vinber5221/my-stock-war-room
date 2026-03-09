import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 1. 介面優化
st.set_page_config(page_title="爸爸的 100 萬實戰選股器", layout="centered")
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}

st.markdown("""<style>.stApp { background-color: #0e1117; color: white; } .stock-card { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }</style>""", unsafe_allow_html=True)

# 2. 繞道抓取引擎 (直接抓官網表格，不走 API)
@st.cache_data(ttl=600)
def get_bypass_data():
    try:
        # 直接抓取今日行情與三大法人匯總表
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # 抓行情 (BW001L 格式)
        p_url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
        p_res = requests.get(p_url, headers=headers, timeout=20).json()
        p_df = pd.DataFrame(p_res['data'], columns=p_res['fields'])
        
        # 抓法人 (T86 格式)
        c_url = f"https://www.twse.com.tw/fund/T86?response=json&date={datetime.now().strftime('%Y%m%d')}&selectType=ALL"
        c_res = requests.get(c_url, headers=headers, timeout=20).json()
        c_df = pd.DataFrame(c_res['data'], columns=c_res['fields'])

        # 清洗：統一欄位名稱
        p_df = p_df[['證券代號', '證券名稱', '收盤價', '漲跌價']].rename(columns={'證券代號':'Code', '證券名稱':'Name'})
        c_df = c_df[['證券代號', '外陸資買賣超股數', '投信買賣超股數']].rename(columns={'證券代號':'Code'})
        
        merged = pd.merge(p_df, c_df, on='Code')
        for col in ['收盤價', '漲跌價', '外陸資買賣超股數', '投信買賣超股數']:
            merged[col] = pd.to_numeric(merged[col].astype(str).str.replace(',', ''), errors='coerce')
        
        merged['ChangePct'] = (merged['漲跌價'] / (merged['收盤價'] - merged['漲跌價'])) * 100
        return merged
    except Exception as e:
        return str(e)

# 3. 介面
st.title("🛡️ 100 萬模擬實戰 (繞道穩贏版)")
st.write(f"💰 現金餘額：${st.session_state.balance:,.0f}")

if st.button("🚀 強制連線掃描"):
    with st.spinner("正在破解塞車路段，直連證交所數據庫..."):
        df = get_bypass_data()
        
        if isinstance(df, str):
            st.error(f"連線失敗：證交所今日數據尚未出爐或維護中。")
            st.info("💡 爸爸，這代表官方還沒放資料出來，我們 15:30 再按一次！")
        else:
            targets = df[(df['外陸資買賣超股數'] > 0) & (df['投信買賣超股數'] > 0) & (df['ChangePct'] >= 2.0)]
            
            if not targets.empty:
                st.success(f"🎯 成功繞道！找到 {len(targets)} 檔強勢股：")
                for _, row in targets.head(15).iterrows():
                    with st.container():
                        st.markdown(f"""<div class="stock-card"><h3 style='color:#00ffc8;'>{row['Name']} ({row['Code']})</h3>
                        <b>漲幅：{row['ChangePct']:.2f}%</b> | 價：{row['收盤價']}<br>
                        <small>外資買：{int(row['外陸資買賣超股數']/1000)}張 / 投信買：{int(row['投信買賣超股數']/1000)}張</small></div>""", unsafe_allow_html=True)
                        if st.button(f"🛒 買進 {row['Name']}", key=row['Code']):
                            cost = row['收盤價'] * 1000
                            if st.session_state.balance >= cost:
                                st.session_state.balance -= cost
                                st.toast(f"✅ 已買入 {row['Name']}")
                                st.rerun()
            else:
                st.warning("數據已連線，但今日尚未出現符合「雙買+大漲」的股票。")
