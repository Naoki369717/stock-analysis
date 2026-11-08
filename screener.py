"""
需給スコアリング・スクリーニングエンジン
相場全体が急落する局面でも、需給面で「最も健全」「アク抜けが先行」「反発余地が大きい」
優良銘柄をスコアリングしてランキング抽出します。
"""

import pandas as pd
from analyzer import fetch_stock_daily, fetch_margin_history, analyze_supply_demand

# 監視対象の注目銘柄プール（半導体・AIインフラ・防衛・海運・金融・商社など）
SCREENING_POOL = {
    "285A": "キオクシアHD",
    "5801": "古河電気工業",
    "5802": "住友電気工業",
    "5803": "フジクラ",
    "6857": "アドバンテスト",
    "8035": "東京エレクトロン",
    "6920": "レーザーテック",
    "6146": "ディスコ",
    "7011": "三菱重工業",
    "7012": "川崎重工業",
    "7203": "トヨタ自動車",
    "9984": "ソフトバンクG",
    "8306": "三菱UFJフィナンシャルG",
    "9101": "日本郵船",
    "8058": "三菱商事",
    "6501": "日立製作所"
}

def scan_god_stocks(target_dict: dict = None) -> list:
    if target_dict is None:
        target_dict = SCREENING_POOL

    results = []
    
    for code, name in target_dict.items():
        try:
            ticker = f"{code}.T"
            df_price = fetch_stock_daily(ticker, period="3mo")
            df_margin = fetch_margin_history(ticker)
            if df_price.empty or df_margin.empty:
                continue
                
            summary = analyze_supply_demand(df_price, df_margin)
            
            divergence = summary["pnl_divergence_pct"]
            buy_change = summary["buy_change"]
            buy_vol = summary["margin_buy_vol"]
            ratio = summary["margin_ratio"]
            turnover_days = summary["turnover_days"]
            is_swapping = summary["is_swapping"]
            
            prev_buy = buy_vol - buy_change
            change_pct = (buy_change / prev_buy * 100) if prev_buy > 0 else 0
            
            # スコアリング（100点満点）
            # 1. 出来高回転スピード（消化が早いほど高得点、最大40点）
            score_turnover = max(0, min(40, int((2.0 - turnover_days) * 20)))
            
            # 2. 買い残の減少度（アク抜け度合い、最大30点）
            score_reduction = max(0, min(30, int(abs(min(0, change_pct)) * 3)))
            if change_pct < 0:
                score_reduction += 10
                
            # 3. 買値との乖離（しこりの浅さ、最大30点）
            score_divergence = max(0, min(30, int((divergence + 35) * 0.8)))
            
            total_score = score_turnover + score_reduction + score_divergence
            
            # シグナル分類
            if divergence > 0:
                tag = "☀️ 青天井・含み益優位"
                badge = "badge-safe"
                desc = f"株価は平均買値より **+{divergence:.1f}% 高値圏**。上値にしこり玉がなく、強い上昇力を維持。"
            elif change_pct < -1.0:
                tag = "💎 アク抜け・底打ち先行"
                badge = "badge-safe"
                desc = f"買い残が前週比 **{change_pct:.1f}% 減少（{buy_change:,.0f}株）**。レバレッジ勢の整理が進み、反発準備が進行中。"
            elif turnover_days <= 0.3:
                tag = "⚡ 超高回転・需給吸収"
                badge = "badge-caution"
                desc = f"買い残消化日数がわずか **{turnover_days}日分**。商いが極めて厚く、需給の重さを出来高で粉砕できる状態。"
            else:
                tag = "⏳ 需給整理待ち"
                badge = "badge-alert"
                desc = f"推定買値から **{divergence:.1f}% 乖離**。急落後の戻り売りゾーンを消化する時間が必要。"

            results.append({
                "code": code,
                "name": name,
                "score": total_score,
                "tag": tag,
                "badge": badge,
                "price": summary["latest_price"],
                "vwap": summary["vwap_est_buy_price"],
                "divergence": divergence,
                "buy_change": buy_change,
                "change_pct": round(change_pct, 1),
                "turnover_days": turnover_days,
                "ratio": ratio,
                "desc": desc
            })
        except Exception:
            continue

    # 総合スコア順にソート
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results
