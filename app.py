import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from analyzer import fetch_stock_daily, fetch_margin_history, analyze_supply_demand
from ai_advisor import generate_ai_report

# ページ基本設定
st.set_page_config(
    page_title="需給レーダー | 株式需給分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 銘柄マスタ定義
DEFAULT_STOCKS = {
    "285A": "キオクシアHD",
    "6723": "ルネサスエレクトロニクス",
    "6857": "アドバンテスト",
    "8035": "東京エレクトロン",
    "6920": "レーザーテック",
    "7203": "トヨタ自動車"
}

# さわやかなモダンUIデザイン用CSS（スマホ完全最適化）
st.markdown("""
<style>
    /* 全体フォント＆背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* ヘッダーのStreamlit標準要素（Fork, GitHub, Deployバッジ等）をスッキリ非表示 */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }
    #MainMenu, footer, [data-testid="stToolbar"] {
        visibility: hidden;
        display: none;
    }
    
    /* アプリタイトルバー */
    .app-header {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        color: white;
        padding: 18px 20px;
        border-radius: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px -2px rgba(37, 99, 235, 0.25);
    }
    .app-header h1 {
        color: white !important;
        font-size: 1.35rem !important;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .app-header p {
        color: #e0f2fe;
        font-size: 0.8rem;
        margin: 4px 0 0 0;
    }

    /* 需給警告・ステータスバナー */
    .status-banner-alert {
        background-color: #fff1f2;
        border-left: 5px solid #f43f5e;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-banner-normal {
        background-color: #f0fdf4;
        border-left: 5px solid #22c55e;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .status-alert-title { color: #e11d48; }
    .status-normal-title { color: #16a34a; }
    .status-body {
        color: #475569;
        font-size: 0.85rem;
        line-height: 1.45;
        margin: 0;
    }

    /* 指標カードグリッド */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    @media (min-width: 768px) {
        .metric-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
    }
    .metric-card {
        background: white;
        padding: 14px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.04);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .metric-sub {
        font-size: 0.72rem;
        font-weight: 600;
    }
    .sub-down { color: #ef4444; }
    .sub-up { color: #22c55e; }
    .sub-neutral { color: #64748b; }

    /* タブデザインの洗練 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #e2e8f0;
        padding: 4px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 8px;
        color: #64748b;
        font-weight: 600;
        font-size: 0.85rem;
        border: none !important;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        background-color: white !important;
        color: #2563eb !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
</style>
""", unsafe_allow_html=True)

# サイドバー：銘柄選択・操作
with st.sidebar:
    st.markdown("### ⚙️ 銘柄選択・設定")
    selected_code = st.selectbox(
        "分析銘柄を選択",
        options=list(DEFAULT_STOCKS.keys()),
        format_func=lambda x: f"{x} - {DEFAULT_STOCKS[x]}"
    )
    
    ticker_input = st.text_input("他の銘柄コードを追加 (例: 7203)", "")
    if st.button("銘柄切替", use_container_width=True) and ticker_input:
        selected_code = ticker_input.strip()
    
    st.markdown("---")
    api_key_input = st.text_input("Gemini API Key (更新用)", type="password")
    if api_key_input:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f"GEMINI_API_KEY={api_key_input}\n")
        st.success("APIキーを更新しました")

ticker_code = f"{selected_code}.T"
stock_name = DEFAULT_STOCKS.get(selected_code, f"銘柄 {selected_code}")

# ヘッダー描画
st.markdown(f"""
<div class="app-header">
    <h1>📈 需給レーダー <span style="font-size:0.9rem; font-weight:normal; opacity:0.9;">[{selected_code}] {stock_name}</span></h1>
    <p>株価・出来高・信用残高から「ポジションの入れ替わり（スワップ）」をリアルタイム診断</p>
</div>
""", unsafe_allow_html=True)

# データ取得
with st.spinner(f"データを取得中..."):
    try:
        df_price = fetch_stock_daily(ticker_code, period="6mo")
        df_margin = fetch_margin_history(ticker_code)
        summary = analyze_supply_demand(df_price, df_margin)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        st.stop()

# ステータス・スワップ警告バナー
if summary["is_swapping"]:
    st.markdown(f"""
    <div class="status-banner-alert">
        <div class="status-title status-alert-title">⚠️ 【需給警告】ポジションの入れ替わり（スワップ）を検知</div>
        <p class="status-body">{summary['swap_comment']}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="status-banner-normal">
        <div class="status-title status-normal-title">✅ 需給ステータス正常</div>
        <p class="status-body">{summary['swap_comment']}</p>
    </div>
    """, unsafe_allow_html=True)

# 指標カード（2x2グリッド）
st.markdown(f"""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-label">現在株価</div>
        <div class="metric-value">{summary['latest_price']:,.0f} <span style="font-size:0.8rem; font-weight:normal;">円</span></div>
        <div class="metric-sub sub-neutral">基準日: {summary['latest_date']}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">推定しこり買値 (VWAP)</div>
        <div class="metric-value">{summary['vwap_est_buy_price']:,.0f} <span style="font-size:0.8rem; font-weight:normal;">円</span></div>
        <div class="metric-sub sub-down">{summary['pnl_divergence_pct']:+.1f}% 乖離</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">信用買い残</div>
        <div class="metric-value">{summary['margin_buy_vol']:,.0f} <span style="font-size:0.8rem; font-weight:normal;">株</span></div>
        <div class="metric-sub {'sub-up' if summary['buy_change']>=0 else 'sub-down'}">前週比: {summary['buy_change']:+,.0f} 株</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">信用倍率 / 消化日数</div>
        <div class="metric-value">{summary['margin_ratio']:.2f} <span style="font-size:0.8rem; font-weight:normal;">倍</span></div>
        <div class="metric-sub sub-neutral">消化目安: {summary['turnover_days']} 日分</div>
    </div>
</div>
""", unsafe_allow_html=True)

# タブ表示
tab1, tab2, tab3 = st.tabs(["📊 チャート分析", "🤖 AI需給診断", "📋 信用残高データ"])

with tab1:
    # 2軸サブプロット（上段: 株価＆VWAP、下段: 信用買い残）
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("株価推移 & 推定しこりゾーン", "信用買い残高 (株)"),
        row_heights=[0.65, 0.35]
    )
    
    # 1. 株価折れ線
    fig.add_trace(
        go.Scatter(
            x=df_price.index,
            y=df_price["Close"],
            name="終値",
            line=dict(color="#2563eb", width=2.2),
            hovertemplate="%{x|%Y-%m-%d}<br>終値: %{y:,.0f} 円<extra></extra>"
        ),
        row=1, col=1
    )
    
    # 2. 推定平均買値ライン
    fig.add_hline(
        y=summary["vwap_est_buy_price"],
        line_dash="dash",
        line_color="#ef4444",
        line_width=1.8,
        annotation_text=f"しこり買値 ({summary['vwap_est_buy_price']:,.0f}円)",
        annotation_position="bottom right",
        annotation_font=dict(color="#ef4444", size=10),
        row=1, col=1
    )
    
    # 3. 信用買い残棒グラフ
    fig.add_trace(
        go.Bar(
            x=df_margin["date"],
            y=df_margin["buy_vol"],
            name="信用買残",
            marker_color="#f97316",
            hovertemplate="%{x|%Y-%m-%d}<br>買残: %{y:,.0f} 株<extra></extra>"
        ),
        row=2, col=1
    )
    
    # スマホ向けレイアウト調整：固定ビューポート
    fig.update_layout(
        height=480,
        margin=dict(l=5, r=10, t=28, b=10),
        paper_bgcolor="white",
        plot_bgcolor="#fafafa",
        showlegend=False,
        # X軸・Y軸の固定（スマホでのピンチによるズレを防止）
        xaxis=dict(fixedrange=True, gridcolor="#f1f5f9"),
        xaxis2=dict(fixedrange=True, gridcolor="#f1f5f9"),
        yaxis=dict(fixedrange=True, gridcolor="#f1f5f9"),
        yaxis2=dict(fixedrange=True, gridcolor="#f1f5f9")
    )
    
    # 【最重要】スマホでピンチズーム・ドラッグ移動を発動させない設定
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "staticPlot": False,       # タップでホバー数値は確認可能
            "scrollZoom": False,       # スクロールでのズーム無効
            "displayModeBar": False    # ツールバー（虫眼鏡アイコン等）を非表示
        }
    )

with tab2:
    with st.spinner("AIが需給構造を診断中..."):
        ai_report = generate_ai_report(summary, stock_name=stock_name)
    st.markdown(ai_report)

with tab3:
    display_df = df_margin.copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        display_df.rename(columns={
            "date": "日付",
            "sell_vol": "売残(株)",
            "buy_vol": "買残(株)",
            "sell_change": "売残増減",
            "buy_change": "買残増減",
            "ratio": "信用倍率"
        }),
        use_container_width=True,
        hide_index=True
    )
