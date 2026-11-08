import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
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

# 銘柄保存ファイルのパス
CUSTOM_STOCKS_FILE = "custom_stocks.json"

# 初期デフォルト銘柄リスト
INITIAL_STOCKS = {
    "285A": "キオクシアHD",
    "6723": "ルネサスエレクトロニクス",
    "6857": "アドバンテスト",
    "8035": "東京エレクトロン",
    "6920": "レーザーテック",
    "7203": "トヨタ自動車"
}

def load_stocks() -> dict:
    """登録銘柄を読み込む"""
    stocks = INITIAL_STOCKS.copy()
    if os.path.exists(CUSTOM_STOCKS_FILE):
        try:
            with open(CUSTOM_STOCKS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                stocks.update(saved)
        except Exception:
            pass
    return stocks

def save_stocks(stocks: dict):
    """登録銘柄を保存する"""
    try:
        with open(CUSTOM_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# セッション状態の初期化
if "stock_list" not in st.session_state:
    st.session_state.stock_list = load_stocks()

if "selected_code" not in st.session_state:
    st.session_state.selected_code = "285A"

# さわやかなモダンUIデザイン用CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Noto Sans JP', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* 右上の不要なメニュー・フッター・Manage appを非表示 */
    #MainMenu, footer, .stDeployButton {
        display: none !important;
    }
    
    /* サイドバー開閉トグルボタン（>>）を押しやすく目立たせる */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15);
        margin: 6px 0 0 6px;
    }

    /* アプリタイトルバー */
    .app-header {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
        color: white;
        padding: 16px 18px;
        border-radius: 16px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px -2px rgba(37, 99, 235, 0.25);
    }
    .app-header h1 {
        color: white !important;
        font-size: 1.3rem !important;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .app-header p {
        color: #e0f2fe;
        font-size: 0.78rem;
        margin: 4px 0 0 0;
    }

    /* 需給警告・ステータスバナー */
    .status-banner-alert {
        background-color: #fff1f2;
        border-left: 5px solid #f43f5e;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-banner-normal {
        background-color: #f0fdf4;
        border-left: 5px solid #22c55e;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .status-title {
        font-weight: 700;
        font-size: 0.92rem;
        margin-bottom: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .status-alert-title { color: #e11d48; }
    .status-normal-title { color: #16a34a; }
    .status-body {
        color: #475569;
        font-size: 0.82rem;
        line-height: 1.45;
        margin: 0;
    }

    /* 指標カードグリッド */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-bottom: 18px;
    }
    @media (min-width: 768px) {
        .metric-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
        }
    }
    .metric-card {
        background: white;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.04);
    }
    .metric-label {
        font-size: 0.72rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 3px;
    }
    .metric-value {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .metric-sub {
        font-size: 0.7rem;
        font-weight: 600;
    }
    .sub-down { color: #ef4444; }
    .sub-up { color: #22c55e; }
    .sub-neutral { color: #64748b; }

    /* タブデザイン */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
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

# -------------------------------------------------------------
# ① サイドバー：銘柄追加・管理・API設定
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 銘柄の選択と追加")
    
    # 登録済みリストから選択
    stock_options = list(st.session_state.stock_list.keys())
    current_idx = stock_options.index(st.session_state.selected_code) if st.session_state.selected_code in stock_options else 0
    
    chosen_side = st.selectbox(
        "分析する銘柄",
        options=stock_options,
        index=current_idx,
        format_func=lambda x: f"{x} - {st.session_state.stock_list.get(x, x)}"
    )
    if chosen_side != st.session_state.selected_code:
        st.session_state.selected_code = chosen_side
        st.rerun()

    st.markdown("---")
    st.markdown("#### ➕ 新しい銘柄を登録")
    with st.form("add_stock_sidebar_form", clear_on_submit=True):
        new_code = st.text_input("銘柄コード (例: 9984, 6501)", "").strip().upper()
        new_name = st.text_input("銘柄名 (例: ソフトバンクG)", "").strip()
        add_submitted = st.form_submit_button("銘柄リストに追加して分析", use_container_width=True)
        
        if add_submitted and new_code:
            display_name = new_name if new_name else f"銘柄 {new_code}"
            st.session_state.stock_list[new_code] = display_name
            save_stocks(st.session_state.stock_list)
            st.session_state.selected_code = new_code
            st.success(f"{new_code} ({display_name}) を登録しました！")
            st.rerun()

    # 銘柄削除（デフォルト以外）
    custom_keys = [k for k in st.session_state.stock_list.keys() if k not in INITIAL_STOCKS]
    if custom_keys:
        st.markdown("#### 🗑️ 追加した銘柄の削除")
        del_target = st.selectbox("削除する銘柄", options=custom_keys, format_func=lambda x: f"{x} - {st.session_state.stock_list[x]}")
        if st.button("銘柄を削除", use_container_width=True):
            del st.session_state.stock_list[del_target]
            save_stocks(st.session_state.stock_list)
            if st.session_state.selected_code == del_target:
                st.session_state.selected_code = "285A"
            st.rerun()

    st.markdown("---")
    api_key_input = st.text_input("Gemini API Key (更新用)", type="password")
    if api_key_input:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(f"GEMINI_API_KEY={api_key_input}\n")
        st.success("APIキーを更新しました")

# -------------------------------------------------------------
# ② 画面上部：ワンタップ銘柄切替 ＆ 簡易追加アコーディオン
# -------------------------------------------------------------
with st.expander("🔍 銘柄の切替・新規追加（ここをタップ）", expanded=False):
    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1:
        st.markdown("**登録済み銘柄から選択**")
        chosen_top = st.selectbox(
            "選択",
            options=stock_options,
            index=current_idx,
            format_func=lambda x: f"{x} - {st.session_state.stock_list.get(x, x)}",
            label_visibility="collapsed"
        )
        if chosen_top != st.session_state.selected_code:
            st.session_state.selected_code = chosen_top
            st.rerun()

    with col_sel2:
        st.markdown("**新しい銘柄を即時追加**")
        with st.form("quick_add_form", clear_on_submit=True):
            q_code = st.text_input("コード", placeholder="例: 9984", label_visibility="collapsed").strip().upper()
            q_name = st.text_input("銘柄名 (省略可)", placeholder="銘柄名", label_visibility="collapsed").strip()
            if st.form_submit_button("追加して表示", use_container_width=True) and q_code:
                d_name = q_name if q_name else f"銘柄 {q_code}"
                st.session_state.stock_list[q_code] = d_name
                save_stocks(st.session_state.stock_list)
                st.session_state.selected_code = q_code
                st.rerun()

# -------------------------------------------------------------
# データ取得 & 分析実行
# -------------------------------------------------------------
selected_code = st.session_state.selected_code
ticker_code = f"{selected_code}.T"
stock_name = st.session_state.stock_list.get(selected_code, f"銘柄 {selected_code}")

# ヘッダー描画
st.markdown(f"""
<div class="app-header">
    <h1>📈 需給レーダー <span style="font-size:0.9rem; font-weight:normal; opacity:0.95;">[{selected_code}] {stock_name}</span></h1>
    <p>株価・出来高・信用残高から「ポジションの入れ替わり（スワップ）」をリアルタイム診断</p>
</div>
""", unsafe_allow_html=True)

with st.spinner(f"【{stock_name} ({selected_code})】の需給データを取得・計算中..."):
    try:
        df_price = fetch_stock_daily(ticker_code, period="6mo")
        df_margin = fetch_margin_history(ticker_code)
        summary = analyze_supply_demand(df_price, df_margin)
    except Exception as e:
        st.error(f"データ取得エラー: 銘柄コード「{selected_code}」のデータを取得できませんでした。コードが正しいかご確認ください。({e})")
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
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("株価推移 & 推定しこりゾーン", "信用買い残高 (株)"),
        row_heights=[0.65, 0.35]
    )
    
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
    
    fig.update_layout(
        height=480,
        margin=dict(l=5, r=10, t=28, b=10),
        paper_bgcolor="white",
        plot_bgcolor="#fafafa",
        showlegend=False,
        xaxis=dict(fixedrange=True, gridcolor="#f1f5f9"),
        xaxis2=dict(fixedrange=True, gridcolor="#f1f5f9"),
        yaxis=dict(fixedrange=True, gridcolor="#f1f5f9"),
        yaxis2=dict(fixedrange=True, gridcolor="#f1f5f9")
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "staticPlot": False,
            "scrollZoom": False,
            "displayModeBar": False
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
