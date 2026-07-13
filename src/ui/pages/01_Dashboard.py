"""
📊 ダッシュボード — 品質メトリクス概要

抽出結果の全体像を可視化: メトリクスカード、カバレッジチャート、
ファイル別内訳、時系列推移。
"""

from __future__ import annotations

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.ui.utils import load_latest_result, compute_quality_metrics, load_llm_result
from src.ui.components import metric_card, coverage_color, section_title


def render():
    st.title("📊 ダッシュボード")
    st.caption("抽出品質とシステム状態の概要")

    # データ読み込み
    rule_data = load_latest_result()
    llm_data = load_llm_result()

    if not rule_data:
        st.warning(
            "まだ抽出結果がありません。左のメニューから「▶️ 実行パネル」"
            "を開いてパイプラインを実行してください。"
        )
        return

    metrics = compute_quality_metrics(rule_data)

    # ── サマリーカード行 ──
    section_title("システム概要")

    cols = st.columns(4)
    with cols[0]:
        metric_card(
            str(metrics["total_cases"]),
            "全案件数",
            "green" if metrics["total_cases"] >= 20 else "yellow",
        )
    with cols[1]:
        metric_card(str(metrics["rule_count"]), "ルール数", "green")
    with cols[2]:
        metric_card(
            str(metrics["files_processed"]),
            "処理ファイル数",
            "green",
        )
    with cols[3]:
        mode = metrics["extraction_mode"]
        color = "green" if "rule" in mode else "yellow"
        metric_card(
            mode.replace("_", " ").title(),
            "抽出モード",
            color,
            "rule_based = LLM不要で0円",
        )

    # 抽出日時
    if metrics["extraction_date"]:
        dt = metrics["extraction_date"][:19]
        st.caption(f"🕐 最新抽出: {dt}")

    # ── フィールド別カバレッジ ──
    section_title("フィールド別抽出カバレッジ")

    coverage = metrics.get("field_coverage", {})
    if coverage:
        df = pd.DataFrame([
            {
                "フィールド": field,
                "抽出数": info["count"],
                "カバー率": info["pct"],
                "未抽出": info["total"] - info["count"],
            }
            for field, info in coverage.items()
        ]).sort_values("カバー率", ascending=True)

        col1, col2 = st.columns([3, 2])

        with col1:
            fig = px.bar(
                df,
                x="カバー率",
                y="フィールド",
                orientation="h",
                text=df["カバー率"].apply(lambda x: f"{x:.1f}%"),
                color="カバー率",
                color_continuous_scale=["#f87171", "#facc15", "#4ade80"],
                range_color=[0, 100],
                title="フィールド別カバー率",
            )
            fig.update_layout(
                height=400,
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#cbd5e1",
                xaxis_title="カバー率 (%)",
                yaxis=dict(autorange="reversed"),
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("##### フィールド別詳細")
            for _, row in df.iterrows():
                pct = row["カバー率"]
                color = coverage_color(pct)
                st.markdown(
                    f"**{row['フィールド']}**"
                    f"<div style='display:flex; align-items:center; gap:0.5rem;'>"
                    f"<div style='flex:1; height:8px; background:#1e293b; border-radius:4px;'>"
                    f"<div style='width:{pct}%; height:100%; "
                    f"background:{ {'green':'#4ade80','yellow':'#facc15','red':'#f87171'}.get(color,'#94a3b8') }; "
                    f"border-radius:4px;'></div></div>"
                    f"<span style='font-size:0.8rem; color:#94a3b8;'>{row['抽出数']}/{int(row['抽出数']+row['未抽出'])}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── ファイル別内訳 ──
    section_title("ファイル別案件数")

    per_file = metrics.get("per_file", {})
    if per_file:
        cols = st.columns(len(per_file))
        for i, (fname, count) in enumerate(per_file.items()):
            with cols[i]:
                metric_card(str(count), fname[:20])

    # ── ルール分布 ──
    section_title("ルール分布")

    from src.ui.utils import load_rules

    rules = load_rules()
    if rules:
        df_rules = pd.DataFrame([
            {"フィールド": field, "ルール数": len(rlist)}
            for field, rlist in sorted(rules.items())
        ])

        fig = px.bar(
            df_rules,
            x="フィールド",
            y="ルール数",
            color="ルール数",
            color_continuous_scale="Blues",
            title="フィールド別ルール数",
            text_auto=True,
        )
        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=30, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption(f"📚 全 {df_rules['ルール数'].sum()} ルール / {len(df_rules)} フィールド")

    # ── LLM 結果サマリー（あれば）──
    if llm_data:
        section_title("🤖 LLM 抽出サマリー")
        llm_stats = llm_data.get("stats", {})
        cols = st.columns(3)
        with cols[0]:
            metric_card(str(llm_stats.get("total_cases", 0)), "LLM 抽出案件数")
        with cols[1]:
            metric_card(llm_stats.get("model", "?"), "LLM モデル")
        with cols[2]:
            metric_card(str(llm_stats.get("files_processed", 0)), "処理ファイル数")
