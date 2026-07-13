"""
🔄 フィードバックループ — インタラクティブ確認・修正・ルール自動生成

案件を選択 → 抽出結果確認 → 正否判定 → LLM 分析 → ルール自動書き込み
のフィードバックサイクルをブラウザ上で実現。
"""

from __future__ import annotations

import json
import streamlit as st
from pathlib import Path

from src.ui.utils import (
    load_latest_result,
    get_all_cases,
    flatten_case,
    load_rules,
    run_rule_pipeline,
    run_excel_export,
    PROJECT_ROOT,
)
from src.ui.components import section_title, detail_field, coverage_color


def render():
    st.title("🔄 フィードバックループ")
    st.caption(
        "案件を確認 → 修正 → ルール自動生成までのサイクルをブラウザで実行。"
        "LLM（DeepSeek API）が必要な操作は ⚡ マーク。"
    )

    # ── データ読み込み ──
    data = load_latest_result()
    if not data:
        st.warning("抽出結果がありません。「▶️ 実行パネル」でパイプラインを実行してください。")
        return

    all_cases = get_all_cases(data)
    if not all_cases:
        st.info("案件データが空です。")
        return

    # ── セッション状態初期化 ──
    if "feedback_idx" not in st.session_state:
        st.session_state.feedback_idx = 0
    if "feedback_log" not in st.session_state:
        st.session_state.feedback_log = []
    if "phase" not in st.session_state:
        st.session_state.phase = "review"

    idx = st.session_state.feedback_idx
    total = len(all_cases)

    # ── 進捗表示 ──
    st.progress((idx) / total, text=f"確認進捗: {idx}/{total}")
    num_correct = sum(1 for log in st.session_state.feedback_log if log.get("result") == "correct")
    num_fixed = sum(1 for log in st.session_state.feedback_log if log.get("result") == "fixed")
    cols = st.columns(3)
    cols[0].metric("✅ 確認済み", len(st.session_state.feedback_log))
    cols[1].metric("👍 正解", num_correct)
    cols[2].metric("🔧 修正済み", num_fixed)

    if idx >= total:
        section_title("🎉 全案件確認完了!")
        st.success(f"全 {total} 件の確認が完了しました。")

        if st.button("📊 レポート表示", type="primary"):
            report = {
                "total": total,
                "checked": len(st.session_state.feedback_log),
                "correct": num_correct,
                "fixed": num_fixed,
                "details": st.session_state.feedback_log,
            }
            st.json(report)

        if st.button("🔄 再実行"):
            st.session_state.feedback_idx = 0
            st.session_state.feedback_log = []
            st.session_state.phase = "review"
            st.rerun()
        return

    # ── 現在の案件 ──
    case = all_cases[idx]
    f = flatten_case(case)

    st.divider()
    st.markdown(f"##### 案件 {idx + 1}/{total}")

    # ── 案件概要 ──
    with st.expander("📋 案件詳細を表示", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="detail-card">', unsafe_allow_html=True)
            detail_field("案件名", f["案件名"])
            detail_field("ファイル", f["ファイル"])
            detail_field("必須スキル", f["必須スキル"])
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="detail-card">', unsafe_allow_html=True)
            detail_field("勤務地", f["勤務地"] or "—")
            detail_field("期間", f"{f['開始日']} 〜 {f['終了日'] or '長期'}")
            detail_field("単価", f"¥{f['単価(下限)']}~{f['単価(上限)']}万/月" if f["単価(下限)"] else "—")
            detail_field("日本語レベル", f["日本語レベル"])
            detail_field("面接回数", str(f["面接回数"]) if f["面接回数"] else "—")
            st.markdown("</div>", unsafe_allow_html=True)

        with st.expander("📄 原文"):
            st.text((case.get("original_text") or "")[:3000])

    # ── 判定 ──
    section_title("抽出結果は正しいですか？")

    col_yes, col_no, col_skip = st.columns(3)

    if col_yes.button("✅ 正しい", use_container_width=True, type="primary"):
        st.session_state.feedback_log.append({
            "idx": idx,
            "project": f["案件名"],
            "result": "correct",
        })
        st.session_state.feedback_idx += 1
        st.session_state.phase = "review"
        st.rerun()

    if col_skip.button("⏭ スキップ", use_container_width=True):
        st.session_state.feedback_idx += 1
        st.rerun()

    if col_no.button("❌ 修正が必要", use_container_width=True, type="secondary"):
        st.session_state.phase = "fix"
        st.rerun()

    # ── 修正フロー ──
    if st.session_state.phase == "fix":
        st.divider()
        section_title("🔧 修正フロー")

        st.info(
            "問題を特定して修正します。⚡ のついた操作は DeepSeek API が必要です。"
        )

        col_field, col_problem = st.columns(2)

        with col_field:
            target_field = st.selectbox(
                "問題があるフィールド",
                [
                    "skill_requirement",
                    "preferred_skills",
                    "period",
                    "rate",
                    "project_name",
                    "location",
                    "japanese_level",
                    "headcount",
                    "interviews",
                    "industry",
                    "trade_flow",
                ],
                index=0,
                help="ルール抽出で問題があったフィールドを選択",
            )

        with col_problem:
            user_feedback = st.text_area(
                "問題の説明",
                placeholder="例: スキルに Python が足りない / 期間が8月じゃなくて7月から / 単価が間違ってる",
                height=80,
            )

        if st.button("⚡ LLM で分析", type="primary", disabled=not user_feedback.strip()):
            with st.spinner("DeepSeek API で分析中..."):
                try:
                    from src.llm_fix import analyze_and_fix

                    result = analyze_and_fix(
                        original_text=case.get("original_text", ""),
                        rule_result=case,
                        user_feedback=user_feedback,
                        target_field=target_field if target_field else None,
                    )
                    st.session_state.llm_result = result
                    st.session_state.phase = "llm_review"
                    st.rerun()
                except Exception as e:
                    st.error(f"LLM分析に失敗しました: {e}")
                    st.info(
                        "原因: DeepSeek API Key が設定されていないか、"
                        "ネットワークエラーの可能性があります。"
                    )

    # ── LLM分析結果表示 ──
    if st.session_state.get("phase") == "llm_review":
        result = st.session_state.get("llm_result", {})
        analysis = result.get("analysis", "")
        corrections = result.get("corrections", {})
        confidence = result.get("confidence", 0)

        st.divider()
        section_title("🤖 LLM 分析結果")

        # 分析テキスト
        st.markdown(f'<div class="detail-card">{analysis}</div>', unsafe_allow_html=True)

        # 確信度
        conf_pct = confidence * 100
        conf_color = "green" if conf_pct >= 80 else "yellow"
        st.markdown(
            f"確信度: <span class='status-badge {conf_color}'>{conf_pct:.0f}%</span>",
            unsafe_allow_html=True,
        )

        # 修正提案
        if corrections:
            section_title("修正提案")
            for field, value in corrections.items():
                if isinstance(value, list):
                    st.markdown(f"**{field}**:")
                    for v in value:
                        st.markdown(f"- {v}")
                else:
                    st.markdown(f"**{field}**: {value}")

        st.session_state.phase = "llm_decision"

    # ── 修正決定 ──
    if st.session_state.get("phase") == "llm_decision":
        st.divider()
        section_title("この修正で正しいですか？")

        col_accept, col_reject = st.columns(2)

        if col_accept.button("✅ はい、修正を適用", type="primary", use_container_width=True):
            result = st.session_state.get("llm_result", {})
            new_rule_hint = result.get("new_rule_hint", "")

            # ルール生成
            if new_rule_hint:
                try:
                    from src.rule_writer import write_rules_from_feedback

                    target_field = st.session_state.get("target_field")
                    with st.spinner("ルール生成中..."):
                        write_rules_from_feedback(
                            original_text=case.get("original_text", ""),
                            user_feedback=user_feedback if "user_feedback" in dir() else "",
                            llm_analysis=result.get("analysis", ""),
                            corrections=result.get("corrections", {}),
                            target_field=target_field,
                            auto_confirm=True,
                        )
                    st.success("✅ 新しいルールをルールライブラリに追加しました。")
                except Exception as e:
                    st.error(f"ルール生成に失敗しました: {e}")

            st.session_state.feedback_log.append({
                "idx": idx,
                "project": f["案件名"],
                "result": "fixed",
                "field": st.session_state.get("target_field", ""),
                "feedback": user_feedback if "user_feedback" in dir() else "",
            })

            st.session_state.phase = "done"

        if col_reject.button("❌ いいえ、スキップ", use_container_width=True):
            st.session_state.feedback_log.append({
                "idx": idx,
                "project": f["案件名"],
                "result": "skipped",
            })
            st.session_state.phase = "done"

    # ── 完了後、次へ ──
    if st.session_state.get("phase") == "done":
        st.divider()
        if st.button("次の案件へ →", type="primary", use_container_width=True):
            st.session_state.feedback_idx += 1
            st.session_state.phase = "review"
            if "llm_result" in st.session_state:
                del st.session_state.llm_result
            st.rerun()

    # ── フィードバックログ ──
    with st.expander("📋 フィードバック履歴"):
        if st.session_state.feedback_log:
            st.json(st.session_state.feedback_log)
        else:
            st.info("まだフィードバックがありません。")
