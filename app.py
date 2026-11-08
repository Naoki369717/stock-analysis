import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

from analyzer import fetch_stock_daily, fetch_margin_history, analyze_supply_demand
from ai_advisor import generate_ai_report

# ページ設定 (スマホ対応レスポンシブ)
st.set_page_config(
    page_title="株式需給分析ダッシュボード",
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
    "6920": "レーザーテック"
}

# カスタムCSS（スマホ最適化）
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 12px;
        border: 1px solid #e9ecef;
        margin-bottom: 10px;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 株式需給分析システム")
st.caption("価格帯・出来高・信用残高の『スワップ（入れ替わり）』をリアルタイム診断")

# サイドバー：銘柄選択・設定
with st.sidebar:
    st.header("⚙️ 設定・銘柄選択")
    
    # 銘柄追加・選択
    selected_code = st.selectbox(
        "分析する銘柄",
        options=list(DEFAULT_STOCKS.keys()),
        format_func=lambda x: f"{x} - {DEFAULT_STOCKS[x]}"
    )
    
    ticker_input = st.text_input("他の銘柄コードを追加 (例: 7203)", "")
    if st.button("銘柄追加") and ticker_input:
        selected_code = ticker_input.strip()
    
    st.divider()
    api_key_input = st.text_input("Gemini API Key (更新する場合)", type="password")
    if api_key_input:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f"GEMINI_API_KEY={api_key_input}\n")
        st.success("APIキーを保存しました")

ticker_code = f"{selected_code}.T"
stock_name = DEFAULT_STOCKS.get(selected_code, f"銘柄 {selected_code}")

# データ取得
with st.spinner(f"【{stock_name} ({selected_code})】の需給データを自動取得中..."):
    try:
        df_price = fetch_stock_daily(ticker_code, period="6mo")
        df_margin = fetch_margin_history(ticker_code)
        summary = analyze_supply_demand(df_price, df_margin)
    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {e}")
        st.stop()

# 警告・アラート表示
if summary["is_swapping"]:
    st.error(f"⚠️ **【需給警告】ポジションの入れ替わり（スワップ）を検知**\n\n{summary['swap_comment']}")
else:
    st.info(f"ℹ️ **需給ステータス**: {summary['swap_comment']}")

# 主要指標カード (スマホで2列/4列表示)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("現在株価", f"{summary['latest_price']:,.0f} 円")
with col2:
    st.metric(
        "推定しこり買値(VWAP)", 
        f"{summary['vwap_est_buy_price']:,.0f} 円", 
        f"{summary['pnl_divergence_pct']:+.1f}%",
        delta_color="inverse"
    )
with col3:
    st.metric(
        "信用買い残", 
        f"{summary['margin_buy_vol']:,.0f} 株", 
        f"{summary['buy_change']:+,.0f} 株",
        delta_color="inverse"
    )
with col4:
    st.metric("信用倍率", f"{summary['margin_ratio']:.2f} 倍")

st.markdown("---")

# タブ表示（①チャート分析 ②AI診断レポート ③生データ）
tab1, tab2, tab3 = st.tabs(["📈 需給・株価チャート", "🤖 Gemini 需給診断", "📋 信用残高データ一覧"])

with tab1:
    st.subheader("株価推移・推定買値・信用買い残")
    
    # Plotlyでスマホでも拡大縮小できる2軸チャート
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        subplot_titles=("株価と直近推定買値ライン (VWAP)", "信用買い残の推移 (株数)"),
        row_heights=[0.65, 0.35]
    )
    
    # 1. ローソク足/終値チャート
    fig.add_trace(
        go.Scatter(
            x=df_price.index, 
            y=df_price["Close"], 
            name="株価 (終値)",
            line=dict(color="#1f77b4", width=2)
        ),
        row=1, col=1
    )
    
    # 2. 推定平均買値ライン
    fig.add_hline(
        y=summary["vwap_est_buy_price"], 
        line_dash="dash", 
        line_color="#d62728",
        annotation_text=f"推定しこりゾーン ({summary['vwap_est_buy_price']:,.0f}円)", 
        annotation_position="bottom right",
        row=1, col=1
    )
    
    # 3. 信用買い残チャート
    fig.add_trace(
        go.Bar(
            x=df_margin["date"], 
            y=df_margin["buy_vol"], 
            name="信用買い残",
            marker_color="#ff7f0e"
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=550,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader(f"🤖 Gemini AI による需給見通し診断")
    with st.spinner("AIが需給構造とスワップ状況を分析中..."):
        ai_report = generate_ai_report(summary, stock_name=stock_name)
    st.markdown(ai_report)

with tab3:
    st.subheader("週次 信用取引残高 推移")
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
        use_container_width=True
    )
