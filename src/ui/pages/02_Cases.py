"""
📋 案件一覧 — 全案件のブラウズ・検索・詳細表示

ソースファイルフィルター、キーワード検索、テーブル一覧、
クリックで詳細パネル（全フィールド表示）。
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.ui.utils import load_latest_result, get_all_cases, flatten_case
from src.ui.components import section_title, detail_field


def render():
    st.title("📋 案件一覧")
    st.caption("抽出結果の全案件をブラウズ・確認")

    data = load_latest_result()
    if not data:
        st.warning("抽出結果がありません。「▶️ 実行パネル」でパイプラインを実行してください。")
        return

    all_cases = get_all_cases(data)

    if not all_cases:
        st.info("案件データが空です。")
        return

    # ── フィルター ──
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        source_files = ["すべて"] + sorted(
            set(c.get("_source_file", "") for c in all_cases)
        )
        selected_file = st.selectbox("📁 ソースファイル", source_files)

    with col2:
        search = st.text_input("🔍 検索（案件名・スキル）", placeholder="例: SAP, Java, PM")

    with col3:
        show_detail = st.checkbox("👁 詳細表示", value=True)

    # ── フィルタリング ──
    filtered = all_cases
    if selected_file != "すべて":
        filtered = [c for c in filtered if c.get("_source_file") == selected_file]
    if search:
        q = search.lower()
        filtered = [
            c
            for c in filtered
            if q in (c.get("project_name") or "").lower()
            or any(q in (s or "").lower() for s in c.get("skill_requirement", []) or [])
        ]

    st.success(f"全 {len(all_cases)} 件中 {len(filtered)} 件を表示")

    if not filtered:
        st.info("該当する案件がありません。")
        return

    # ── テーブル表示 ──
    rows = []
    for c in filtered:
        f = flatten_case(c)
        rows.append({
            "案件名": f["案件名"][:50],
            "ファイル": f["ファイル"][:20],
            "スキル数": f["スキル数"],
            "勤務地": f["勤務地"] or "—",
            "期間": f["開始日"] or "—",
            "日本語": f["日本語レベル"],
            "単価": f"¥{f['単価(下限)']}~{f['単価(上限)']}万" if f["単価(下限)"] else "—",
            "面接": f["面接回数"] or "—",
            "_idx": rows.__len__(),
        })

    df = pd.DataFrame(rows)

    st.dataframe(
        df.drop(columns=["_idx"]),
        use_container_width=True,
        height=min(400, 40 * len(filtered)),
        column_config={
            "案件名": st.column_config.TextColumn(width="large"),
            "スキル数": st.column_config.NumberColumn(width="small"),
            "単価": st.column_config.TextColumn(width="small"),
            "日本語": st.column_config.TextColumn(width="small"),
        },
        hide_index=True,
    )

    # ── 案件選択 → 詳細表示 ──
    if not show_detail:
        return

    section_title("案件詳細")

    case_names = [f"{c.get('project_name','?')[:60]} [{c.get('_source_file','')}]" for c in filtered]
    selected_idx = st.selectbox(
        "詳細を表示する案件を選択",
        range(len(filtered)),
        format_func=lambda i: case_names[i],
        label_visibility="collapsed",
    )

    case = filtered[selected_idx]
    f = flatten_case(case)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        detail_field("案件名", f["案件名"])
        detail_field("ファイル", f["ファイル"])
        detail_field("スキル数", str(f["スキル数"]))
        detail_field("必須スキル", f["必須スキル"])
        if f["歓迎スキル"]:
            detail_field("歓迎スキル", f["歓迎スキル"])
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        detail_field("勤務地", f["勤務地"] or "—")
        detail_field("最寄駅", f["最寄駅"] or "—")
        detail_field("リモート", f["リモート"])
        detail_field("期間", f"{f['開始日']} 〜 {f['終了日'] or '長期'}")
        detail_field("単価", f"¥{f['単価(下限)']} 〜 ¥{f['単価(上限)']} 万/月" if f["単価(下限)"] else "—")
        detail_field("募集人数", str(f["募集人数"]) if f["募集人数"] else "—")
        detail_field("業種", f["業種"] or "—")
        detail_field("契約形態", f["契約形態"] or "—")
        st.markdown("</div>", unsafe_allow_html=True)

    col3, col4 = st.columns([1, 1])

    with col3:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        detail_field("日本語レベル", f["日本語レベル"])
        detail_field("英語レベル", f["英語レベル"] or "—")
        detail_field("面接回数", str(f["面接回数"]) if f["面接回数"] else "—")
        detail_field("即日参画", f["即日参画"])
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="detail-card">', unsafe_allow_html=True)
        detail_field("備考", f["備考"] or "—")
        st.markdown("</div>", unsafe_allow_html=True)

    # 原文表示（折りたたみ）
    with st.expander("📄 案件原文（original_text）"):
        orig = (case.get("original_text") or "")[:5000]
        if orig:
            st.text(orig)
        else:
            st.info("原文がありません。")

    # ── スキルクラウド（タグ表示）──
    if f["必須スキル"]:
        section_title("必須スキルタグ")
        html = "".join(f'<span class="tag">{s}</span>' for s in f["必須スキル"])
        st.markdown(f'<div>{html}</div>', unsafe_allow_html=True)
