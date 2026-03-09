import yfinance as yf
import plotly.graph_objects as go

# 新增個股查詢功能
st.divider()
st.subheader("🔍 個股實時走勢")
target = st.text_input("輸入股票代碼 (例如: 2330)", value="2330")

if target:
    # 轉換成 yfinance 格式 (台股需加 .TW)
    symbol = f"{target}.TW"
    
    # 抓取實時數據 (間隔 5 分鐘)
    data = yf.download(symbol, period="1d", interval="5m")
    
    if not data.empty:
        # 繪製專業 K 線圖
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='K線'
        )])
        
        fig.update_layout(
            title=f"{target} 今日 5 分鐘 K 線圖",
            xaxis_rangeslider_visible=False,
            template="plotly_dark", # 深色模式更有質感
            height=400,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # 顯示即時漲跌
        curr_price = data['Close'].iloc[-1]
        open_price = data['Open'].iloc[0]
        diff = curr_price - open_price
        st.metric("當前價格", f"{curr_price:.2f}", f"{diff:.2f}")
    else:
        st.warning("找不到該個股數據，請確認代碼是否正確。")
