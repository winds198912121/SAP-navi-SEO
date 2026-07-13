"""
📚 ルール管理 — ルールライブラリの表示・検索・テスト

フィールド別ルール一覧、正規表現テスト、ルール統計の可視化。
"""

from __future__ import annotations

import json
import re
import streamlit as st
import pandas as pd
import plotly.express as px

from src.ui.utils import load_rules, RULES_PATH
from src.ui.components import section_title


def render():
    st.title("📚 ルール管理")
    st.caption("ルールライブラリの表示・検索・テスト")

    rules = load_rules()

    if not rules:
        st.warning(f"ルールファイルが見つかりません: {RULES_PATH}")
        return

    total = sum(len(v) for v in rules.values())
    st.success(f"📚 全 {total} ルール / {len(rules)} フィールド")

    # ── ルール分布 ──
    section_title("ルール分布")

    df = pd.DataFrame([
        {"フィールド": field, "ルール数": len(v)} for field, v in sorted(rules.items())
    ])

    col1, col2 = st.columns([3, 2])

    with col1:
        fig = px.bar(
            df,
            x="フィールド",
            y="ルール数",
            color="ルール数",
            color_continuous_scale="Viridis",
            text_auto=True,
        )
        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=10, b=80),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### フィールド別ルール数")
        for _, row in df.iterrows():
            bar_width = int(row["ルール数"] / df["ルール数"].max() * 100)
            st.markdown(
                f"<small>{row['フィールド']}</small>"
                f"<div style='display:flex; align-items:center; gap:0.5rem;'>"
                f"<div style='flex:1; height:6px; background:#1e293b; border-radius:3px;'>"
                f"<div style='width:{bar_width}%; height:100%; "
                f"background:#818cf8; border-radius:3px;'></div></div>"
                f"<span style='font-size:0.8rem;'>{row['ルール数']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── フィールド選択 → ルール一覧 ──
    section_title("ルール詳細")

    col_f, col_s = st.columns([1, 2])

    with col_f:
        selected_field = st.selectbox(
            "フィールドを選択",
            [""] + sorted(rules.keys()),
            format_func=lambda x: "（選択してください）" if not x else x,
        )

    with col_s:
        search_rule = st.text_input("🔍 ルール検索（ID or 説明）", placeholder="例: period, skill, jp_")

    if selected_field:
        field_rules = rules.get(selected_field, [])

        # 検索フィルタ
        if search_rule:
            q = search_rule.lower()
            field_rules = [
                r
                for r in field_rules
                if q in r.get("id", "").lower() or q in r.get("description", "").lower()
            ]

        st.markdown(f"**{selected_field}**: {len(field_rules)} ルール")

        if field_rules:
            tab1, tab2 = st.tabs(["📋 一覧", "🧪 テスト"])

            with tab1:
                # ルールカード表示
                for rule in field_rules:
                    rid = rule.get("id", "?")
                    desc = rule.get("description", "")
                    pattern = rule.get("pattern", "")
                    priority = rule.get("priority", 50)

                    with st.expander(f"[{rid}] {desc}"):
                        col_p, col_info = st.columns([3, 1])

                        with col_p:
                            st.code(pattern, language="regex", line_numbers=False)

                        with col_info:
                            st.markdown(f"**優先度:** {priority}")
                            st.markdown(f"**ID:** `{rid}`")
                            if rule.get("field"):
                                st.markdown(f"**フィールド:** {rule['field']}")

            with tab2:
                # ルールテスト
                st.markdown("##### 正規表現テスト")
                test_text = st.text_area(
                    "テストテキストを入力",
                    placeholder="例: 作業期間：2026/07/01～長期",
                    height=100,
                    key="rule_test_text",
                )

                test_rule_id = st.selectbox(
                    "テストするルール",
                    [r["id"] for r in field_rules],
                    format_func=lambda rid: f"[{rid}] {next((r['description'] for r in field_rules if r['id']==rid), '')}",
                )

                if st.button("テスト実行", type="primary") and test_text:
                    rule = next((r for r in field_rules if r["id"] == test_rule_id), None)
                    if rule and test_text:
                        try:
                            matches = re.findall(rule["pattern"], test_text)
                            if matches:
                                st.success(f"✅ マッチしました！ ({len(matches)} 件)")
                                for m in matches[:10]:
                                    st.code(str(m))
                            else:
                                st.warning("❌ マッチしませんでした")
                        except re.error as e:
                            st.error(f"正規表現エラー: {e}")

        else:
            st.info("該当するルールがありません。")

    st.divider()

    # ── ルールファイル情報 ──
    section_title("ルールファイル情報")

    if RULES_PATH.exists():
        stat = RULES_PATH.stat()
        col_info, col_dl = st.columns([2, 1])

        with col_info:
            st.markdown(f"**パス:** `{RULES_PATH}`")
            st.markdown(f"**サイズ:** {stat.st_size / 1024:.1f} KB")
            st.markdown(f"**更新日:** {pd.Timestamp.fromtimestamp(stat.st_mtime)}")

        with col_dl:
            with open(RULES_PATH, encoding="utf-8") as f:
                content = f.read()
            st.download_button(
                "⬇️ ルールファイルをダウンロード",
                data=content,
                file_name="field_rules.json",
                mime="application/json",
                use_container_width=True,
            )
