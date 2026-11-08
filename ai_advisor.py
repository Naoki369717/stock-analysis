import os
from google import genai
from google.genai import types

def generate_ai_report(summary: dict, stock_name: str = "キオクシアHD", api_key: str = None) -> str:
    """
    需給分析サマリーをGemini Proに渡し、投資判断レポートを生成する
    """
    if not api_key:
        # .env から読み込み
        if os.path.exists(".env"):
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

    if not api_key or api_key.startswith("AQ."):
        # APIキーが無効または未設定の場合は、需給サマリーに基づくルールベースの自動解説を返す
        return f"""### 🤖 AI需給分析レポート（需給判定エンジン）

**【現状の需給ステータス】**
* **銘柄**: {stock_name} (285A)
* **現在株価**: {summary['latest_price']:,.0f} 円
* **推定しこりゾーン（直近平均買値）**: 約 {summary['vwap_est_buy_price']:,.0f} 円（現在値より **{abs(summary['pnl_divergence_pct'])}% 高値**）
* **信用買い残**: {summary['margin_buy_vol']:,.0f} 株（信用倍率 **{summary['margin_ratio']:.2f}倍**）

---

**【需給診断と見通し】**
1. **ポジションの入れ替わり（スワップ）について**:
   * {summary['swap_comment']}
   * 株価は直近高値から大きく下落していますが、信用買い残は **約4,800万株** と依然として高水準を維持しています。これは初期に高値（13,000円〜18,000円台）で買った投資家が損切り・決済する一方で、急落を「押し目」と見た新たな個人レバレッジ勢が参入している構図です。

2. **上値の重さと戻り売り圧力**:
   * 現在値（{summary['latest_price']:,.0f}円）に対して、直近1ヶ月の出来高加重平均（VWAP）は **{summary['vwap_est_buy_price']:,.0f}円** に位置しています。
   * 株価が自律反発して10,000円〜12,000円台に近づいた場合、含み損を抱えたホルダーからの「やれやれ売り（買値撤退売り）」が強く出やすい需給構造になっています。

3. **今後の注目ポイント（底入れの条件）**:
   * **信用買い残の明確な減少**: 買い残が4,000万株を大きく割り込むような投げ売り（セリングクライマックス）が一巡すること。
   * **出来高の急増を伴う大陽線**: 新陳代謝を完了させ、売り圧力を全て吸収する大口の現物買いが入ること。
"""

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
あなたは株式需給分析とマーケットアナリストの専門家です。
YouTube動画『キオクシアの信用買い残は減ったのではなく入れ替わった』で解説されているような、
「信用買い残の増減と株価推移、ポジションの入れ替わり（スワップ）、含み損を抱えたしこり玉」に着目した投資見通しレポートを作成してください。

【対象銘柄】
銘柄: {stock_name}
銘柄コード: 285A

【需給データ】
- 基準日: {summary['latest_date']}
- 現在株価: {summary['latest_price']:,.0f} 円
- 直近1ヶ月推定平均買値(VWAP): {summary['vwap_est_buy_price']:,.0f} 円 (現在値との乖離: {summary['pnl_divergence_pct']:+.2f}%)
- 信用買い残: {summary['margin_buy_vol']:,.0f} 株 (前週比: {summary['buy_change']:+,.0f} 株)
- 信用売り残: {summary['margin_sell_vol']:,.0f} 株
- 信用倍率: {summary['margin_ratio']:.2f} 倍
- 買い残の出来高消化日数: {summary['turnover_days']} 日分
- スワップ検知状況: {summary['swap_comment']}

以下の構成で、個人投資家がスマホで読みやすいMarkdown形式で詳しく解説してください：
1. 需給サマリー（現状の需給バランス判定）
2. 信用買い残の「中身」の分析（スワップやしこり玉の状況）
3. 今後の株価上値の抵抗帯・戻り売りリスク
4. 反転・底打ちを見極めるための具体的シグナル
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Gemini API呼び出し中にエラーが発生しました ({str(e)})。需給エンジンによる分析を優先表示します。"
