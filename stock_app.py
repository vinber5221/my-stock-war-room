import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime

# 1. 頁面優化
st.set_page_config(page_title="100萬實戰-終極穩定版", layout="centered")
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0

st.markdown("""<style>.stApp { background-color: #0e1117; color: white; } .stock-card { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }</style>""", unsafe_allow_html=True)

# 2. 終極數據引擎 (抓取法人 CSV + 行情 CSV)
@st.cache_data(ttl=300)
def get_final_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    today_str = datetime.now().strftime('%Y%m%d')
    
    try:
        # A. 抓取法人買賣超 (CSV 格式)
        c_url = f"https://www.twse.com.tw/fund/T86?response=csv&date={today_str}&selectType=ALL"
        c_res = requests.get(c_url, headers=headers, timeout=20)
        c_lines = c_res.text.split('\n')
        # 移除 CSV 的頭尾雜訊
        c_data = [l for l in c_lines if len(l.split('","')) > 10]
        c_df = pd.read_csv(io.StringIO('\n'.join(c_data)))
        
        # B. 抓取今日行情 (CSV 格式)
        p_url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
        p_df = pd.read_csv(p_url)
        
        # C. 整理與合併 (關鍵：過濾掉非個股)
        p_df = p_df[['證券代號', '證券名稱', '收盤價', '漲跌價']].rename(columns={'證券代號':'Code', '證券名稱':'Name'})
        c_df = c_df.iloc[:, [0, 7, 10]] # 取 證券代號, 外資買賣超, 投信買賣超
        c_df.columns = ['Code', 'Foreign', 'Trust']
        
        # 清洗代號中的引號
        c_df['Code'] = c_df['Code'].astype(str).str.replace('=', '').str.replace('"', '')
        p_df['Code'] = p_df['Code'].astype(str)
        
        merged = pd.merge(p_df, c_df, on='Code')
        
        # 轉換數字
        for col in ['收盤價', '漲跌價', 'Foreign', 'Trust']:
            merged[col] = pd.to_numeric(merged[col].astype(str).str.replace(',', ''), errors='coerce')
        
        merged['ChangePct'] = (merged['漲跌價'] / (merged['收盤價'] - merged['漲跌價'])) * 100
        return merged
    except Exception as e:
        return str(e)

# 3. 介面
st.title("🛡️ 100萬實戰-終極穩定版")
st.subheader(f"💰 目前餘額：${st.session_state.balance:,.0f}")

if st.button("🚀 啟動終極掃描 (直連 CSV 通道)"):
    with st.spinner("正在讀取證交所原始數據檔..."):
        df = get_final_data()
        
        if isinstance(df, str):
            st.warning("⚠️ 數據尚未出爐。提示：法人籌碼通常在 15:00-15:30 之間發佈。")
        else:
            # 篩選：外資買 > 0 且 投信買 > 0 且 漲幅 > 2%
            targets = df[(df['Foreign'] > 0) & (df['Trust'] > 0) & (df['ChangePct'] >= 2.0)].sort_values(by='ChangePct', ascending=False)
            
            if not targets.empty:
                st.success(f"🎯 成功！偵測到 {len(targets)} 檔法人鎖碼股")
                for _, row in targets.head(20).iterrows():
                    with st.container():
                        st.markdown(f"""<div class="stock-card">
                        <h3 style='color:#00ffc8; margin:0;'>{row['Name']} ({row['Code']})</h3>
                        <p style='font-size:1.2rem; margin:10px 0;'>🔥 漲幅：{row['ChangePct']:.2f}% | 價：{row['收盤價']}</p>
                        <p style='color:#aaa; font-size:0.9rem;'>外資買：{int(row['Foreign']/1000
