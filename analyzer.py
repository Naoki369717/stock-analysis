"""
株式需給分析エンジン (Market Supply & Demand Analysis Engine)
キオクシアなどの銘柄の株価・出来高および信用残高を自動取得・分析します。
"""

import sys
import requests
import bs4
import pandas as pd
import yfinance as yf
from datetime import datetime

# Windowsコンソールでの文字化け防止
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def fetch_stock_daily(ticker_code: str = "285A.T", period: str = "3mo") -> pd.DataFrame:
    """yfinanceから日足株価データを取得"""
    print(f"[{ticker_code}] 日足データを取得中 ({period})...")
    df = yf.download(ticker_code, period=period, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        # MultiIndexの解除
        df.columns = [col[0] for col in df.columns]
    df.index = pd.to_datetime(df.index)
    return df

def fetch_margin_history(ticker_code: str = "285A.T") -> pd.DataFrame:
    """Yahoo!ファイナンスから週次信用残高の履歴を取得"""
    clean_code = ticker_code.replace(".T", "")
    url = f"https://finance.yahoo.co.jp/quote/{clean_code}/margin"
    print(f"[{clean_code}] 信用残高データを取得中 ({url})...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    
    soup = bs4.BeautifulSoup(res.content.decode("utf-8", errors="replace"), "html.parser")
    table = soup.find("table")
    if not table:
        raise ValueError("信用残高テーブルが見つかりませんでした。")
        
    rows = []
    for tr in table.find_all("tr"):
        cols = [c.text.strip().replace("\n", "").replace(",", "") for c in tr.find_all(["th", "td"])]
        if cols and cols[0] != "日付":
            # 日付, 売残, 買残, 売残増減, 買残増減, 信用倍率
            try:
                date = cols[0]
                sell_vol = float(cols[1]) if cols[1] not in ["-", ""] else 0.0
                buy_vol = float(cols[2]) if cols[2] not in ["-", ""] else 0.0
                sell_change = float(cols[3]) if cols[3] not in ["-", ""] else 0.0
                buy_change = float(cols[4]) if cols[4] not in ["-", ""] else 0.0
                ratio = float(cols[5]) if cols[5] not in ["-", ""] else 0.0
                rows.append({
                    "date": pd.to_datetime(date),
                    "sell_vol": sell_vol,
                    "buy_vol": buy_vol,
                    "sell_change": sell_change,
                    "buy_change": buy_change,
                    "ratio": ratio
                })
            except Exception as e:
                continue
                
    margin_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return margin_df

def analyze_supply_demand(df_price: pd.DataFrame, df_margin: pd.DataFrame) -> dict:
    """
    動画の需給ロジックに基づいた指標計算:
    1. 推定平均買値 (Volume Weighted Average Price on accumulation weeks)
    2. しこりゾーン（現在の株価と推定買値の乖離・やれやれ売り圧力）
    3. 信用買い残消化日数 (買い残 ÷ 5日移動平均出来高)
    4. スワップ（入れ替わり）判定
    """
    latest_price = float(df_price["Close"].iloc[-1])
    recent_5d_vol = float(df_price["Volume"].tail(5).mean())
    latest_margin = df_margin.iloc[-1]
    prev_margin = df_margin.iloc[-2] if len(df_margin) > 1 else latest_margin
    
    buy_vol = latest_margin["buy_vol"]
    sell_vol = latest_margin["sell_vol"]
    buy_change = latest_margin["buy_change"]
    
    # 出来高消化日数（今のペースの商いで買い残を市場が吸収するのに何日かかるか）
    turnover_days = round(buy_vol / recent_5d_vol, 1) if recent_5d_vol > 0 else 0.0
    
    # 推定平均買値の簡易試算（直近1ヶ月の出来高加重平均価格 VWAP）
    recent_1m_price = df_price.tail(22)
    vwap = float((recent_1m_price["Close"] * recent_1m_price["Volume"]).sum() / recent_1m_price["Volume"].sum())
    
    # 含み損益の推定乖離率 (%)
    pnl_divergence = round(((latest_price - vwap) / vwap) * 100, 2)
    
    # スワップ判定
    # 株価が下落しているのに買い残があまり減っていない（横ばいまたは微減/増加）
    price_change_recent = (latest_price - float(recent_1m_price["Close"].iloc[0])) / float(recent_1m_price["Close"].iloc[0]) * 100
    is_swapping = False
    swap_comment = ""
    
    if price_change_recent < -10 and buy_vol >= prev_margin["buy_vol"] * 0.9:
        is_swapping = True
        swap_comment = "株価急落局面でも買い残が高止まりしており、高値掴み勢の損切りと底値狙いの新規買いによる『ポジションの入れ替わり（スワップ）』が強く示唆されます。"
    elif buy_vol > prev_margin["buy_vol"]:
        swap_comment = "下落局面での買い残増加傾向が見られ、ナンピン買い・リバウンド狙いのしこり玉が積み上がっています。"
    else:
        swap_comment = "買い残の整理（期日返済や損切り）が一定程度進んでいます。"

    return {
        "latest_price": latest_price,
        "vwap_est_buy_price": round(vwap, 1),
        "pnl_divergence_pct": pnl_divergence,
        "margin_buy_vol": buy_vol,
        "margin_sell_vol": sell_vol,
        "margin_ratio": latest_margin["ratio"],
        "buy_change": buy_change,
        "turnover_days": turnover_days,
        "is_swapping": is_swapping,
        "swap_comment": swap_comment,
        "latest_date": df_price.index[-1].strftime("%Y-%m-%d")
    }

if __name__ == "__main__":
    df_price = fetch_stock_daily("285A.T", period="3mo")
    df_margin = fetch_margin_history("285A.T")
    summary = analyze_supply_demand(df_price, df_margin)
    
    print("\n" + "="*50)
    print("【株式需給分析サマリー】")
    print(f"銘柄コード: 285A (キオクシア)")
    print(f"基準日: {summary['latest_date']}")
    print(f"現在株価: {summary['latest_price']:,.0f} 円")
    print(f"直近推定平均買値: {summary['vwap_est_buy_price']:,.0f} 円 (乖離: {summary['pnl_divergence_pct']:+.2f}%)")
    print(f"信用買い残: {summary['margin_buy_vol']:,.0f} 株 (前週比: {summary['buy_change']:+,.0f} 株)")
    print(f"信用売り残: {summary['margin_sell_vol']:,.0f} 株")
    print(f"信用倍率: {summary['margin_ratio']:.2f} 倍")
    print(f"買い残消化日数: {summary['turnover_days']} 日分 (5日平均出来高ベース)")
    print(f"スワップ検知: {'【警告】入れ替わり発生中' if summary['is_swapping'] else '通常'}")
    print(f"解説メモ: {summary['swap_comment']}")
    print("="*50)
