#!/usr/bin/env python3
"""
솔트룩스 2025년 연간 분석 리포트 대시보드
yfinance 데이터를 수집하여 Plotly로 분석 리포트를 생성
"""

import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def main():
    """메인 실행 함수: 데이터 수집부터 차트 생성까지 수행"""
    # -----------------------------------------------------------------------------
    # 1. 데이터 수집 및 전처리
    # -----------------------------------------------------------------------------
    print("데이터 다운로드 및 전처리 중...")

    # 솔트룩스(304100.KQ) 2025년 전체 데이터 다운로드
    ticker = "304100.KQ"
    start_date = "2025-01-01"
    end_date = "2025-12-31"
    df = yf.download(ticker, start=start_date, end=end_date)

    # MultiIndex 컬럼 처리 (yfinance 최신 버전 호환성)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df.columns = df.columns.get_level_values(0)
        except Exception: # pylint: disable=broad-exception-caught
            pass

    # 인덱스가 날짜 형식이 아닐 경우 변환
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # -----------------------------------------------------------------------------
    # 1.1 주요 지표 계산
    # -----------------------------------------------------------------------------
    # 가격 정보
    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    year_return = ((end_price - start_price) / start_price) * 100
    high_price = df['High'].max()
    low_price = df['Low'].min()

    # 파생 변수 생성
    df['Daily_Return'] = df['Close'].pct_change() * 100  # 일간 수익률
    df['Cumulative_Return'] = ((df['Close'] / start_price) - 1) * 100  # 누적 수익률
    df['Trade_Value'] = df['Volume'].mul(df['Close'])  # 거래대금

    # 이동평균선 (Short/Mid/Long)
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    # 볼린저밴드 (20일, ±2 표준편차)
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    df['BB_Std'] = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'].add(df['BB_Std'].mul(2))
    df['BB_Lower'] = df['BB_Middle'].sub(df['BB_Std'].mul(2))

    # 변동성 및 리스크 지표
    daily_volatility = df['Daily_Return'].std()
    annual_volatility = daily_volatility * (252 ** 0.5)  # 연환산 변동성
    df['Rolling_Volatility'] = df['Daily_Return'].rolling(window=20).std()

    # MDD (최대 낙폭) 계산
    df['Cummax'] = df['Close'].expanding().max()
    df['Drawdown'] = ((df['Close'].sub(df['Cummax'])).div(df['Cummax'])) * 100
    mdd = df['Drawdown'].min()

    # 월별 데이터 집계
    df['Month'] = df.index.month
    monthly_data = df.groupby('Month').agg({'Close': ['first', 'last']})
    monthly_data.columns = ['First', 'Last']
    monthly_data['Return'] = (
        (monthly_data['Last'] - monthly_data['First']) / monthly_data['First']
    ) * 100
    monthly_trade = df.groupby('Month')['Trade_Value'].mean()

    # 거래 패턴 분석
    df['Price_Change'] = df['Close'].sub(df['Open'])
    df['Is_Up'] = df['Price_Change'] > 0  # 상승 마감 여부
    avg_volume = df['Volume'].mean()
    volume_std = df['Volume'].std()
    df['Volume_Spike'] = df['Volume'] > (avg_volume + 2 * volume_std)  # 거래량 급증

    # 통계 요약 데이터
    total_days = len(df)
    up_days = df['Is_Up'].sum()
    down_days = total_days - up_days
    win_rate = (up_days / total_days) * 100 if total_days > 0 else 0
    avg_gain = df[df['Daily_Return'] > 0]['Daily_Return'].mean()
    avg_loss = df[df['Daily_Return'] < 0]['Daily_Return'].abs().mean()
    profit_loss_ratio = avg_gain / avg_loss if avg_loss > 0 else 0
    sharpe_ratio = (
        (year_return - 3) / annual_volatility if annual_volatility > 0 else 0
    )

    print("전처리 완료. 통합 대시보드 생성 중...")

    # -----------------------------------------------------------------------------
    # 레이아웃 구성 (7행 그리드 - 가변 간격 구현)
    # Row 1: KPI (간격 좁게)
    # Row 2: Main Chart
    # Row 3: SPACER (빈 행 - 간격 넓게 효과)
    # Row 4: Monthly
    # Row 5: Pattern
    # Row 6: Risk
    # Row 7: Table
    # -----------------------------------------------------------------------------
    fig = make_subplots(
        rows=7, cols=6,
        specs=[
            [{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}],  # Row 1
            [{'colspan': 6, 'type': 'xy'}, None, None, None, None, None],           # Row 2
            [None, None, None, None, None, None],                                   # Row 3 (Spacer)
            [{'colspan': 3, 'type': 'xy'}, None, None,
             {'colspan': 3, 'type': 'xy'}, None, None],                             # Row 4
            [{'colspan': 2, 'type': 'xy'}, None, {'colspan': 2, 'type': 'xy'},
             None, {'colspan': 2, 'type': 'xy'}, None],                             # Row 5
            [{'colspan': 3, 'type': 'xy'}, None, None,
             {'colspan': 3, 'type': 'xy'}, None, None],                             # Row 6
            [{'colspan': 6, 'type': 'table'}, None, None, None, None, None]         # Row 7
        ],
        vertical_spacing=0.02,  # 기본 간격을 매우 좁게 설정 (KPI와 차트 사이)
        horizontal_spacing=0.03,
        subplot_titles=(
            None, None, None, None, None, None,
            "Price Flow & Trend (주가 흐름)",
            "Monthly Returns (월별 수익률)", "Monthly Trade Value (월별 거래대금)",
            "Trade Patterns (거래 패턴)", "Rolling Volatility (20일 변동성)",
            "Return Distribution (수익률 분포)",
            "Drawdown Risk (최대 낙폭)", "Cumulative Return (누적 수익률)",
            "Statistical Summary (통계 요약)"
        ),
        # Row 3에 0.03 할당 -> 위아래 gap 0.02 + 0.03 + 0.02 = 0.07 (충분한 간격)
        row_heights=[0.05, 0.21, 0.03, 0.175, 0.175, 0.175, 0.185] # 메인 차트 축소(0.35->0.21) 및 하단 영역 확대
    )

    # -------------------------------------------------------------------------
    # Row 1: KPI Indicators (핵심 지표)
    # -------------------------------------------------------------------------
    indicators = [
        ("연초가", start_price, "number", ""),
        ("연말가", end_price, "number", ""),
        ("수익률", year_return, "number+delta", "%"),
        ("최고가", high_price, "number", ""),
        ("최저가", low_price, "number", ""),
        ("MDD", mdd, "number", "%"),
    ]

    for i, (title, val, mode, suffix) in enumerate(indicators):
        fig.add_trace(go.Indicator(
            mode=mode, value=val,
            title={'text': title, 'font': {'size': 14, 'color': 'gray'}},
            number={'suffix': suffix, 'font': {'size': 24}},
            delta={'reference': 0} if "delta" in mode else None
        ), row=1, col=i+1)

    # -------------------------------------------------------------------------
    # Row 2: Main Chart (주가 흐름)
    # -------------------------------------------------------------------------
    # 캔들스틱 (기본 차트)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price', increasing_line_color='#26A69A', decreasing_line_color='#EF5350',
        hovertemplate=(
            "<b>Date</b>: %{x|%Y-%m-%d}<br>"
            "<b>Open</b>: %{open:,.0f}<br>"
            "<b>High</b>: %{high:,.0f}<br>"
            "<b>Low</b>: %{low:,.0f}<br>"
            "<b>Close</b>: %{close:,.0f}<br>"
            "<extra></extra>"  # 범례 이름 제거
        )
    ), row=2, col=1)

    # 라인 차트 (버튼으로 전환용, 초기에는 숨김)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        mode='lines', line=dict(color='#26A69A', width=2),
        name='Close Line', visible=False,  # 초기 상태는 숨김
        hovertemplate="<b>Date</b>: %{x|%Y-%m-%d}<br><b>Close</b>: %{y:,.0f}<extra></extra>"
    ), row=2, col=1)

    # 볼린저밴드 (채널 표시)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_Upper'],
        line=dict(color='gray', width=1, dash='dot'),
        name='BB Upper', showlegend=True
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['BB_Lower'],
        line=dict(color='gray', width=1, dash='dot'),
        name='BB Lower', fill='tonexty', fillcolor='rgba(200,200,200,0.1)', showlegend=True
    ), row=2, col=1)

    # 이동평균선
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA20'],
        line=dict(color='#2962FF', width=1.5), name='MA20'
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA60'],
        line=dict(color='#FF6D00', width=1.5), name='MA60'
    ), row=2, col=1)

    # -------------------------------------------------------------------------
    # Row 3: Spacer (Empty)
    # -------------------------------------------------------------------------
    # No traces added here. Used only for spacing.

    # -------------------------------------------------------------------------
    # Row 4: Monthly Analysis (월별 분석)
    # -------------------------------------------------------------------------
    months = list(range(1, 13))
    mon_ret = monthly_data['Return'].reindex(months, fill_value=0)
    mon_trade = monthly_trade.reindex(months, fill_value=0)

    # 월별 수익률
    colors_ret = ['#26A69A' if x > 0 else '#EF5350' for x in mon_ret]
    fig.add_trace(go.Bar(
        x=months, y=mon_ret, marker_color=colors_ret,
        name='Monthly Ret', showlegend=False
    ), row=4, col=1) # Row 3 -> 4

    # 월별 거래대금
    fig.add_trace(go.Bar(
        x=months, y=mon_trade, marker_color='#5C6BC0',
        name='Avg Trade', showlegend=False
    ), row=4, col=4) # Row 3 -> 4

    # -------------------------------------------------------------------------
    # Row 5: Pattern & Volatility (거래패턴 및 변동성)
    # -------------------------------------------------------------------------
    # 거래대금 패턴 (상승일/하락일 구분)
    colors_vol = ['#26A69A' if up else '#EF5350' for up in df['Is_Up']]
    fig.add_trace(go.Bar(
        x=df.index, y=df['Trade_Value'], marker_color=colors_vol,
        name='Trade Val', showlegend=False
    ), row=5, col=1) # Row 4 -> 5

    # 이동 변동성
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Rolling_Volatility'],
        line=dict(color='#AB47BC', width=1.5),
        name='Vol(20d)', showlegend=False
    ), row=5, col=3) # Row 4 -> 5

    # 수익률 분포 (히스토그램)
    fig.add_trace(go.Histogram(
        x=df['Daily_Return'], marker_color='#7E57C2', nbinsx=40,
        name='Dist', showlegend=False
    ), row=5, col=5) # Row 4 -> 5

    # -------------------------------------------------------------------------
    # Row 6: Risk & Cumulative (리스크 및 누적 성과)
    # -------------------------------------------------------------------------
    # Drawdown (낙폭)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Drawdown'], fill='tozeroy',
        line=dict(color='#C62828', width=1),
        name='DD', showlegend=False
    ), row=6, col=1) # Row 5 -> 6

    # 누적 수익률
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Cumulative_Return'], fill='tozeroy',
        line=dict(color='#1565C0', width=2),
        name='Cum Ret', showlegend=False
    ), row=6, col=4) # Row 5 -> 6

    # -------------------------------------------------------------------------
    # Row 7: Table (통계 테이블)
    # -------------------------------------------------------------------------
    stats_data = [
        ['Total Days', 'Up Days (Win Rate)', 'Down Days', 'Avg Gain', 'Avg Loss',
         'P/L Ratio', 'Ann Volatility', 'Sharpe Ratio', 'Ann Return', 'Max Drawdown'],
        [f"{total_days}", f"{up_days} ({win_rate:.1f}%)", f"{down_days}",
         f"+{avg_gain:.2f}%", f"-{avg_loss:.2f}%", f"{profit_loss_ratio:.2f}",
         f"{annual_volatility:.1f}%", f"{sharpe_ratio:.2f}",
         f"{year_return:.1f}%", f"{mdd:.1f}%"]
    ]

    fig.add_trace(go.Table(
        header=dict(values=["Metric", "Value"], fill_color='#455A64',
                    font=dict(color='white', size=12), align='left'),
        cells=dict(values=stats_data, fill_color='#F5F5F5', align='left', height=30)
    ), row=7, col=1) # Row 6 -> 7

    # -------------------------------------------------------------------------
    # 최종 레이아웃 다듬기
    # -------------------------------------------------------------------------
    fig.update_layout(
        title_text="<b>Saltlux (304100.KQ) 2025 Annual Analysis Report</b>",
        title_x=0.5,
        height=2200, # 10개 항목 모두 표시를 위한 높이 추가 확보
        template="plotly_white",
        margin=dict(l=40, r=40, t=120, b=40),
        hovermode="x unified",
        # 범례 위치 수정: 메인 차트(Row 2) 내부 우측 상단에 배치
        legend=dict(
            orientation="h",
            yanchor="top",
            y=0.90,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255, 255, 255, 0.5)"
        ),
        # ---------------------------------------------------------------------
        # 버튼 메뉴 (Chart Style & Indicator Toggle)
        # ---------------------------------------------------------------------
        updatemenus=[
            # 1. 차트 스타일 전환 (캔들스틱 vs 라인) - 좌측
            dict(
                type="buttons",
                direction="left",
                active=0,
                x=0.01, y=0.92,  # 메인 차트 바로 위 좌측
                buttons=list([
                    dict(label="Candle",
                         method="update",
                         # Visible: [KPI*6, Candle, Line, BB*2, MA*2, Rest...]
                         args=[{"visible": [True]*6 + [True, False] + [True]*30}]),
                    dict(label="Line",
                         method="update",
                         args=[{"visible": [True]*6 + [False, True] + [True]*30}])
                ]),
            ),
            # 2. 보조지표 토글 (볼린저 밴드 On/Off) - 우측 (Side-by-Side)
            dict(
                type="buttons",
                direction="left",
                showactive=True,
                x=0.12, y=0.92, # 차트 스타일 버튼 우측에 배치 (같은 높이)
                buttons=list([
                    dict(label="BB On",
                         method="restyle",
                         args=["visible", True, [8, 9]]), # Trace 8, 9는 BB Upper/Lower
                    dict(label="BB Off",
                         method="restyle",
                         args=["visible", False, [8, 9]])
                ]),
            )
        ]
    )

    # 메인 차트에만 Range Slider 활성화 (두께 줄여서 겹침 방지)
    fig.update_xaxes(rangeslider_visible=False)
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.03), # 두께 3%로 축소
        row=2, col=1
    )

    # 그리드 및 Spikolines (십자선) 설정
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor='#ECEFF1',
        showspikes=True, spikemode='across', spikesnap='cursor', showline=True, spikedash='dash'
    )
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor='#ECEFF1',
        showspikes=True, spikemode='across', spikesnap='cursor', showline=True, spikedash='dash'
    )



    # 대화형 실행 (모드바 설정 포함)
    fig.show(
        config={
            'displayModeBar': True,
            'modeBarButtonsToAdd': [
                'drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'
            ],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'saltlux_chart',
                'height': 1200,
                'width': 1800,
                'scale': 2
            }
        }
    )
    print("통합 대시보드 생성 완료.")

if __name__ == "__main__":
    main()
