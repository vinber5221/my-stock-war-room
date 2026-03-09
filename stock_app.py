import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime

# 1. 頁面優化與資金記憶
st.set_page_config(page_title="100萬實戰-終極出水版", layout="centered")
if 'balance' not in st.session_state: st.session_state.balance = 1000000.0
if 'portfolio' not in st.session_state: st.session_state.portfolio = {}

st.markdown("""<style>.stApp { background-color: #0e1117; color: white; } .stock-card { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }</style>""", unsafe_allow_html=True)

# 2. 終極數據引擎 (三路併進)
@st.cache_data(ttl=300)
def get_final_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    today_str = datetime.now().strftime('%Y%m%d')
    
    try:
        # A. 抓取法人買賣超 (CSV 備援通道)
        c_url = f"https://www.twse.com.tw/fund/T86?response=csv&date={today_str}&selectType=ALL"
        c_res = requests.get(c_url, headers=headers, timeout=20)
        c_lines = c_res.text.split('\n')
        c_data = [l for l in c_lines if len(l.split('","')) > 10]
        if not c_data: return "籌碼數據尚未更新"
        c_df = pd.read_csv(io.StringIO('\n'.join(c_data)))
        
        # B. 抓取今日行情 (穩定 Open Data 通道)
        p_url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
        p_df = pd.read_csv(p_url)
        
        # C. 數據清洗與欄位對接
        p_df = p_df[['證券代號', '證券名稱', '收盤價', '漲跌價']].rename(columns={'證券代號':'Code', '證券名稱':'Name'})
        # 自動抓取正確的法人欄位 (外資在第7欄, 投信在第10欄)
        c_df = c_df.iloc[:, [0, 7, 10]]
        c_df.columns = ['Code', 'Foreign', 'Trust']
        
        # 清除代號格式 (例如把 ="2330" 轉成 2330)
        c_df['Code'] = c_df['Code'].astype(str).str.replace('=', '').str.replace('"', '')
        p_df['Code'] = p_df['Code'].astype(str)
        
        merged = pd.merge(p_df, c_df, on='Code')
        
        # 轉數字並計算漲幅
        for col in ['收盤價', '漲跌價', 'Foreign', 'Trust']:
            merged[col] = pd.to_numeric(merged[col].astype(str).str.replace(',', ''), errors='coerce')
        
        merged['ChangePct'] = (merged['漲跌價'] / (merged['收盤價'] - merged['漲跌價'])) * 100
        return merged
    except Exception as e:
        return f"系統連線中: {str(e)}"

# 3. 介面呈現
st.title("🛡️ 100萬實戰-終極出水版")
st.subheader(f"💰 目前餘額：${st.session_state.balance:,.0f}")

# 顯示持倉
if st.session_state.portfolio:
    with st.expander("💼 我的持倉庫存"):
        for c, info in list(st.session_state.portfolio.items()):
            st.write(f"📈 {c} | {info['張數']}張 | 成本: {info['成本']}")
            if st.button(f"賣出 {c}", key=f"s_{c}"):
                st.session_state.balance += (info['成本'] * 1000)
                del st.session_state.portfolio[c]
                st.rerun()

if st.button("🚀 啟動終極掃描 (直連備援通道)"):
    with st.spinner("正在破解塞車路段，直連證交所數據庫..."):
        df = get_final_data()
        
        if isinstance(df, str):
            st.warning(f"⚠️ {df}。建議 16:00 後數據最完整。")
        else:
            # 篩選條件：外資 > 0 且 投信 > 0 且 漲幅 >= 2.0%
            targets = df[(df['Foreign'] > 0) & (df['Trust'] > 0) & (df['ChangePct'] >= 2.0)].sort_values(by='ChangePct', ascending=False)
            
            if not targets.empty:
                st.success(f"🎯 偵測到 {len(targets)} 檔法人鎖碼強勢股：")
                for _, row in targets.head(15).iterrows():
                    with st.container():
                        st.markdown(f"""<div class="stock-card">
                        <h3 style='color:#00ffc8; margin:0;'>{row['Name']} ({row['Code']})</h3>
                        <p style='font-size:1.2rem; margin:10px 0;'>🔥 漲幅：{row['ChangePct']:.2f}% | 價：{row['收盤價']}</p>
                        <p style='color:#aaa; font-size:0.9rem;'>外資買超：{int(row['Foreign']/1000):,} 張 / 投信買超：{int(row['Trust']/1000):,} 張</p>
                        </div>""", unsafe_allow_html=True)
                        if st.button(f"🛒 模擬買進 1 張 {row['Name']}", key=f"b_{row['Code']}"):
                            cost = row['收盤價'] * 1000
                            if st.session_state.balance >= cost:
                                st.session_state.balance -= cost
                                name_key = f"{row['Name']}({row['Code']})"
                                st.session_state.portfolio[name_key] = {'張數': 1, '成本': row['收盤價']}
                                st.success(f"✅ 已買入 {row['Name']}")
                                st.rerun()
            else:
                st.info("目前尚無符合「雙買+大漲」標的，請稍後再試。")

st.divider()
st.caption("提示：若多次失敗，請點擊網頁重新整理。")
