"""
需給分析診断エンジン (Dynamic Supply & Demand Analysis Engine)
銘柄ごとの株価・四本値・出来高・信用残高の実数値から、
動画のロジックに基づく完全個別・動的な診断レポートを自動生成します。
"""

def generate_dynamic_report(summary: dict, stock_name: str, code: str) -> str:
    """銘柄のリアルタイム計算データに基づく動的レポート生成"""
    
    price = summary['latest_price']
    vwap = summary['vwap_est_buy_price']
    divergence = summary['pnl_divergence_pct']
    buy_vol = summary['margin_buy_vol']
    sell_vol = summary['margin_sell_vol']
    ratio = summary['margin_ratio']
    buy_change = summary['buy_change']
    turnover_days = summary['turnover_days']
    is_swapping = summary['is_swapping']
    
    # 乖離状況の判定
    if divergence < -15:
        pnl_status = f"現在の株価（{price:,.0f}円）は直近推定平均買値（{vwap:,.0f}円）を **{abs(divergence):.1f}% 下回る大幅な含み損ゾーン** にあります。"
        res_advice = f"**{vwap:,.0f}円付近** に強い「やれやれ売り（買値撤退売り）」の抵抗帯が形成されており、戻り局面では上値が重くなりやすい構造です。"
    elif divergence < 0:
        pnl_status = f"現在の株価（{price:,.0f}円）は推定平均買値（{vwap:,.0f}円）のやや下（{abs(divergence):.1f}% 乖離）に位置しています。"
        res_advice = f"平均買値の **{vwap:,.0f}円** を明確に上抜けてサポート（下値支持）に転換できるかが反発継続の試金石となります。"
    else:
        pnl_status = f"現在の株価（{price:,.0f}円）は推定買値（{vwap:,.0f}円）を上回っており（+{divergence:.1f}%）、直近の買いポジションは全体として **含み益ゾーン** にあります。"
        res_advice = f"直近エントリー勢の含み損による戻り売り圧力は軽微であり、**{vwap:,.0f}円** が押し目のサポートとして意識されやすい状態です。"

    # 信用倍率と消化日数の判定
    if turnover_days > 3.0:
        digest_eval = f"買い残を市場が吸収するのに **約 {turnover_days}日分の出来高** が必要です。消化に時間がかかる水準であり、一過性の買いでは需給が好転しにくい点に注意が必要です。"
    else:
        digest_eval = f"買い残の出来高消化日数は **約 {turnover_days}日分** と比較的回転が早く、商いの活況さに対して買い残の重みは限定的です。"

    # 信用残増減トレンド
    if buy_change > 0:
        trend_comment = f"直近週で信用買い残が **+{buy_change:,.0f}株増加** しており、レバレッジをかけた新規買い・押し目狙いが活発に流入しています。"
    else:
        trend_comment = f"直近週で信用買い残が **{buy_change:,.0f}株減少** しており、期日返済や手仕舞い売りなどによるポジション整理が進んでいます。"

    # スワップ判定の詳細
    if is_swapping:
        swap_detail = f"""
* ⚠️ **ポジションの入れ替わり（スワップ）発生**:
  株価下落トレンド中にもかかわらず信用買い残が消化されずに高止まりしています。
  これは「以前の高値で捕まった投資家の損切り」と「割安と見て新規参入したリバウンド狙い勢」のポジションが交代しているだけであり、**市場全体のしこり玉（将来の売り圧力）が解消されていない** 状態を示します。
"""
    else:
        swap_detail = f"""
* ℹ️ **スワップ傾向**:
  現時点では極端な高値組と底値組のしこり入れ替わりは検知されておらず、需給バランスは通常の推移（または順調な消化局面）を保っています。
"""

    report = f"""### 📊 【{code}】{stock_name} 需給診断レポート

#### 1. 需給ステータス総括
* **現在株価**: **{price:,.0f} 円**
* **直近推定平均買値 (VWAP)**: **{vwap:,.0f} 円** (現在値との乖離: **{divergence:+.1f}%**)
* **信用倍率**: **{ratio:.2f} 倍** (売残: {sell_vol:,.0f} 株 / 買残: {buy_vol:,.0f} 株)
* **買い残増減**: **{buy_change:+,.0f} 株**

---

#### 2. ポジション構造と「しこり玉」の分析
{pnl_status}
{trend_comment}
{swap_detail}

---

#### 3. 上値抵抗帯と出来高消化力
* **抵抗帯の目安**:
  {res_advice}
* **需給消化力（出来高比）**:
  {digest_eval}

---

#### 4. 今後の注目シグナル
1. **推定買値ライン（{vwap:,.0f}円）へのアプローチ**:
   株価がこの水準に達した際、出来高を伴って突破できるか、あるいは「やれやれ売り」に押されて跳ね返されるかを注視。
2. **信用買い残の推移**:
   {f'買い残（現在 {buy_vol:,.0f}株）の減少傾向が確認できるまで、リバウンド狙いの早すぎるエントリーはリスクを伴います。' if is_swapping else '買い残の急増がないか（新規の過熱がないか）を引き続き監視。'}
"""
    return report

def generate_ai_report(summary: dict, stock_name: str = "キオクシアHD", code: str = "285A", api_key: str = None) -> str:
    # 常に銘柄ごとの実データに基づいた動的レポートを返す
    return generate_dynamic_report(summary, stock_name, code)
