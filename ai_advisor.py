"""
テーマ別 需給カード診断エンジン (Categorized Card-based Diagnosis)
初心者やスマホ利用時でも直感的に理解できるよう、
「トピック（要約見出し）」＋「平易な言葉による解説（用語補足付き）」を
テーマごとのペイン（カード）形式で提供します。
"""

def generate_report_cards(summary: dict, stock_name: str, code: str) -> list:
    """テーマ別に整理された診断カードのリストを生成"""
    
    price = summary['latest_price']
    vwap = summary['vwap_est_buy_price']
    divergence = summary['pnl_divergence_pct']
    buy_vol = summary['margin_buy_vol']
    sell_vol = summary['margin_sell_vol']
    ratio = summary['margin_ratio']
    buy_change = summary['buy_change']
    turnover_days = summary['turnover_days']
    is_swapping = summary['is_swapping']
    
    cards = []

    # テーマ1: 買っている人たちの損得（含み損益としこり玉）
    if divergence < -15:
        t1_status = "alert"
        t1_topic = f"買い手の多くが大きな含み損を抱えている状態（平均買値から約 {abs(divergence):.0f}% 下落）"
        t1_desc = f"""
現在買っている投資家の平均取得コスト（推定）は **約 {vwap:,.0f}円** です。
現在の株価（{price:,.0f}円）はそこから大きく下回っているため、高値で買った投資家の多くが「含み損」を抱えて身動きが取れなくなっています。

💡 **投資への影響（しこり玉とは？）**
「しこり玉」とは、含み損に耐えかねて*「買値まで戻ったら損をせずに売り逃げたい」*と待ち構えている売り圧力のことです。株価が **{vwap:,.0f}円** に近づくほど、このやれやれ売りが強く出て上値が重くなりやすくなります。
"""
    elif divergence < 0:
        t1_status = "caution"
        t1_topic = f"買い手はやや含み損（平均買値 {vwap:,.0f}円 付近でのもみ合い）"
        t1_desc = f"""
現在買っている投資家の平均取得コスト（推定）は **約 {vwap:,.0f}円** で、現在の株価（{price:,.0f}円）は買値のすぐ下（マイナス {abs(divergence):.1f}%）にあります。
含み損はまだ浅いためパニック売りは起きていませんが、**{vwap:,.0f}円** を上抜けて安定できるかどうかが当面の反発の分かれ目になります。
"""
    else:
        t1_status = "safe"
        t1_topic = f"買い手の多くが含み益ゾーン（売り圧力が少ない良好な状態）"
        t1_desc = f"""
現在の株価（{price:,.0f}円）は、直近の平均買値（**約 {vwap:,.0f}円**）を上回っています（プラス {divergence:.1f}%）。
最近買った投資家は利益が出ている状態のため、含み損による「やれやれ売り（逃げの売り）」が頭上にほとんどありません。**{vwap:,.0f}円** 付近は、下がった時の押し目買いサポートとして機能しやすい環境です。
"""

    cards.append({
        "theme": "👥 投資家の心理・損得状況",
        "topic": t1_topic,
        "desc": t1_desc,
        "status": t1_status,
        "tag": "しこり玉・含み損益"
    })

    # テーマ2: ポジションの入れ替わり（スワップ）判定
    if is_swapping:
        t2_status = "alert"
        t2_topic = "高値組の損切りと、新規の底値狙い組が『入れ替わり（スワップ）』中"
        t2_desc = f"""
株価が急落しているにもかかわらず、信用買い残高は **約 {buy_vol:,.0f}株** と高止まりしています。
これは動画でも解説されていた典型例で、「過去の高値で買った投資家が損切りして撤退した分」を、「安くなったと見た新しい個人投資家が買い増している」状態です。

💡 **投資への影響（スワップとは？）**
買い残高の総数が減っていないということは、**「将来売らなければならない借金の玉が、人を変えて残り続けている」**ことを意味します。まだ下値固め（アク抜け）が完了していない可能性があるため、早すぎるリバウンド狙いには注意が必要です。
"""
    elif buy_change > 0:
        t2_status = "caution"
        t2_topic = f"下落中の押し目買いが活発（買い残が前週比 +{buy_change:,.0f}株 増加）"
        t2_desc = f"""
直近1週間で借金して買うポジションが **+{buy_change:,.0f}株** 増えています。
将来上昇すると見込んだ個人投資家の買い意欲は旺盛ですが、もしここから一段安となった場合、これらが新たな「含み損組（将来の売り圧力）」に変わるリスクを孕んでいます。
"""
    else:
        t2_status = "safe"
        t2_topic = f"買いポジションの整理が進展（前週比 {buy_change:,.0f}株 減少）"
        t2_desc = f"""
借金して買っていたポジションが **{buy_change:,.0f}株** 減少し、市場のしこり玉が順調に消化（損切りや利食いによる返済）されています。
過剰なレバレッジの整理が進むほど、将来の上値が軽くなり、需給面では底打ちが近づく好材料となります。
"""

    cards.append({
        "theme": "🔄 ポジションの新陳代謝（スワップ）",
        "topic": t2_topic,
        "desc": t2_desc,
        "status": t2_status,
        "tag": "需給の重さ・健全度"
    })

    # テーマ3: 市場が買い残を消化するスピード（消化日数）
    if turnover_days > 3.0:
        t3_status = "caution"
        t3_topic = f"買い残の重さは中〜重め（現在の商いで消化に 約 {turnover_days}日分 必要）"
        t3_desc = f"""
現在積み上がっている信用買い残（{buy_vol:,.0f}株）は、直近の1日あたり出来高の **約 {turnover_days}日分** に相当します。
市場の商い（取引量）に対して買いポジションの量がやや多いため、出来高が細ると需給悪化の影響を受けやすい水準です。
"""
    else:
        t3_status = "safe"
        t3_topic = f"商いが活発で買い残をスムーズに吸収可能（消化目安: わずか 約 {turnover_days}日分）"
        t3_desc = f"""
買い残の株数（{buy_vol:,.0f}株）に対して日々の出来高が非常に大きいため、**わずか {turnover_days}日分の商い** で買い残全体を市場が回転・吸収できる状態です。
出来高が旺盛なため、需給の重さ自体はそれほど致命的な障害になりにくい環境です。
"""

    cards.append({
        "theme": "⚡ 買い残の重さと消化スピード",
        "topic": t3_topic,
        "desc": t3_desc,
        "status": t3_status,
        "tag": "出来高回転力"
    })

    # テーマ4: 今後の立ち回りとエントリーの見極め
    if is_swapping or divergence < -15:
        t4_topic = f"買い急ぎは禁物。{vwap:,.0f}円までの戻り売り圧力に警戒"
        t4_desc = f"""
* **エントリー判断**:
  現在の下落局面では、安易なナンピン買いや底値拾いは避け、**「買い残の明確な減少」** または **「出来高急増を伴う強い反発」** を待つのが定石です。
* **戻り待ちの目標**:
  上昇した場合も、しこりゾーンである **{vwap:,.0f}円前後** で跳ね返される可能性が高いため、短期リバウンドを狙う際は早めの利益確定が推奨されます。
"""
    else:
        t4_topic = f"需給良好。{vwap:,.0f}円を押し目支持線として意識"
        t4_desc = f"""
* **エントリー判断**:
  極端なしこり玉の重みがないため、業績や相場環境に応じた順張りが通用しやすい需給です。
* **下値メド**:
  直近の平均買値である **{vwap:,.0f}円** 付近まで押した局面は、押し目買いの候補として意識されます。
"""

    cards.append({
        "theme": "🎯 投資戦略・立ち回りの指針",
        "topic": t4_topic,
        "desc": t4_desc,
        "status": "safe" if divergence >= 0 else "caution",
        "tag": "売買アプローチ"
    })

    return cards
