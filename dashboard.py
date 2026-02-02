import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 설정
# pylint: disable=non-ascii-name
종목명 = "솔트룩스"
종목코드 = "304100.KQ"
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

# 데이터 다운로드 및 CSV 저장 (사용자 요청 코드 적용)
print(f"\n{'='*50}")
print(f"{종목명}({종목코드}) 데이터 다운로드 시작...")
print(f"기간: {START_DATE} ~ {END_DATE}")
print(f"{'='*50}\n")

try:
    df = yf.download(종목코드, start=START_DATE, end=END_DATE)

    if not df.empty:
        FILENAME = f"{종목명}_{종목코드.replace('.', '_')}_2025.csv"
        df.to_csv(FILENAME, encoding='utf-8-sig')

        print("✓ 다운로드 성공!")
        print(f"✓ 데이터 개수: {len(df)}개")
        print(f"✓ 저장 파일: {FILENAME}")
        print("\n데이터 미리보기:")
        print(df.head())
        print("\n기본 통계:")
        print(df['Close'].describe())
    else:
        print("✗ 데이터가 없습니다. 종목코드를 확인해주세요.")
        exit()

except Exception as e: # pylint: disable=broad-exception-caught
    print(f"✗ 오류 발생: {e}")
    print("종목코드 형식을 확인해주세요 (예: 035420.KS, 304100.KQ)")
    exit()

print(f"\n{'='*50}")

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# 데이터 가공
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
base_price = df['Close'].iloc[0]
df['Cumulative_Return'] = (df['Close'] - base_price) / base_price * 100

# 지표 계산
current_price = df['Close'].iloc[-1]
prev_price = df['Close'].iloc[-2]

# 차트 레이아웃 구성
fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.15, 0.45, 0.15, 0.25],
    specs=[[{"type": "indicator"}], [{"type": "xy"}], [{"type": "xy"}], [{"type": "xy"}]]
)

# 1. 주요 지표
fig.add_trace(go.Indicator(
    mode="number+delta",
    value=current_price,
    delta={'reference': prev_price, 'relative': True, 'valueformat': '.2%'},
    title={"text": "Current Price (KRW)"},
    domain={'row': 0, 'column': 0}
), row=1, col=1)

# 2. 주가 차트 (캔들 + MA)
fig.add_trace(go.Candlestick(
    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name='OHLC', increasing_line_color='#50C878', decreasing_line_color='#E74C3C'
), row=2, col=1)
fig.add_trace(go.Scatter(
    x=df.index, y=df['MA5'], line=dict(color='orange', width=1), name='MA 5'
), row=2, col=1)
fig.add_trace(go.Scatter(
    x=df.index, y=df['MA20'], line=dict(color='blue', width=1), name='MA 20'
), row=2, col=1)

# 3. 거래량
colors = ['#50C878' if row['Open'] <= row['Close'] else '#E74C3C' for _, row in df.iterrows()]
fig.add_trace(go.Bar(
    x=df.index, y=df['Volume'], marker_color=colors, name='Volume'
), row=3, col=1)

# 4. 수익률
fig.add_trace(go.Scatter(
    x=df.index, y=df['Cumulative_Return'], mode='lines',
    line=dict(color='#50C878' if df['Cumulative_Return'].iloc[-1] >= 0 else '#E74C3C', width=2),
    name='Return (%)', fill='tozeroy', fillcolor='rgba(80, 200, 120, 0.1)'
), row=4, col=1)

# 0% 기준선
fig.add_trace(go.Scatter(
    x=[df.index[0], df.index[-1]], y=[0, 0], mode='lines',
    line=dict(color='gray', dash='dash', width=1), name='Zero Line', hoverinfo='skip'
), row=4, col=1)

# 스타일 및 설정
fig.update_layout(
    title=dict(text='<b>Saltlux (304100.KQ) 2025 Analysis</b>', x=0.5, font=dict(size=24)),
    template='simple_white', height=1200, showlegend=False, margin=dict(l=50, r=50, t=100, b=50)
)

fig.update_xaxes(title_text="Date", row=4, col=1)
fig.update_yaxes(title_text="Price (KRW)", row=2, col=1)
fig.update_yaxes(title_text="Volume", row=3, col=1)
fig.update_yaxes(title_text="Return (%)", row=4, col=1)

fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.05, row=2, col=1)
fig.update_xaxes(matches='x2', row=3, col=1)
fig.update_xaxes(matches='x2', row=4, col=1)

# 차트 출력
fig.show()
