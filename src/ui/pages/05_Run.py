"""
▶️ 実行パネル — パイプライン実行・エクスポート

ルール抽出、LLM 抽出、Excel 出力の実行ボタン。
実行結果と出力ファイル一覧を表示。
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.ui.utils import (
    run_rule_pipeline,
    run_excel_export,
    run_llm_pipeline,
    load_latest_result,
    output_files,
    PROJECT_ROOT,
)
from src.ui.components import section_title, metric_card


def render():
    st.title("▶️ 実行パネル")
    st.caption("パイプライン実行・エクスポート操作")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("##### 📊 ルール抽出")
        st.caption("LLM 不使用、約 0.3 秒、0 円")
        if st.button("🚀 ルール抽出を実行", type="primary", use_container_width=True):
            with st.spinner("ルール抽出パイプライン実行中..."):
                success = run_rule_pipeline()
                if success:
                    st.success("✅ ルール抽出完了！")
                    # 最新結果を確認
                    data = load_latest_result()
                    if data:
                        stats = data.get("stats", {})
                        st.info(
                            f"処理ファイル: {stats.get('files_processed', 0)} | "
                            f"全案件数: {stats.get('total_cases', 0)} | "
                            f"ルール数: {data.get('rule_library', {}).get('total_rules', 0)}"
                        )
                else:
                    st.error("❌ 抽出に失敗しました。コンソールログを確認してください。")

    with col2:
        st.markdown("##### 📗 Excel 出力")
        st.caption("41 列、複数シート")
        if st.button("📗 Excel 出力", use_container_width=True):
            with st.spinner("Excel 生成中..."):
                success = run_excel_export()
                if success:
                    st.success("✅ Excel 出力完了！")
                else:
                    st.error("❌ Excel 出力に失敗しました。")

    with col3:
        st.markdown("##### 🤖 LLM 抽出")
        st.caption("DeepSeek API 使用（要 API Key）")
        if st.button("⚡ LLM 実行", use_container_width=True):
            with st.spinner("LLM 抽出中（数十秒かかることがあります）..."):
                success, logs = run_llm_pipeline()
                if success:
                    st.success("✅ LLM 抽出完了！")
                else:
                    st.error("❌ LLM 抽出に失敗しました。")
                    with st.expander("エラーログ"):
                        st.code(logs[:2000])

    st.divider()

    # ── クイック起動手順 ──
    section_title("💻 CLI クイック起動")

    cli_col1, cli_col2 = st.columns(2)
    with cli_col1:
        st.code(
            "source .venv/bin/activate\n"
            "python3 src/run_pipeline.py && python3 src/export_excel.py",
            language="bash",
        )
    with cli_col2:
        st.code("streamlit run src/ui/app.py", language="bash")

    st.divider()

    # ── 最新結果サマリー ──
    section_title("📊 最新結果サマリー")

    data = load_latest_result()
    if data:
        stats = data.get("stats", {})
        rule_lib = data.get("rule_library", {})

        cols = st.columns(4)
        cols[0].metric("案件数", stats.get("total_cases", 0))
        cols[1].metric("ファイル数", stats.get("files_processed", 0))
        cols[2].metric("ルール数", rule_lib.get("total_rules", 0))
        cols[3].metric("モード", stats.get("extraction_mode", "?"))

        if data.get("extraction_date"):
            st.caption(f"🕐 抽出日時: {data['extraction_date'][:19]}")
    else:
        st.info("まだ結果がありません。上の「ルール抽出を実行」ボタンを押してください。")

    st.divider()

    # ── 出力ファイル一覧 ──
    section_title("📁 出力ファイル一覧")

    files = output_files()
    if files:
        df = pd.DataFrame([
            {
                "ファイル名": f["name"],
                "タイプ": f["suffix"],
                "サイズ": f"{f['size'] / 1024:.1f} KB",
                "更新日時": f["mtime"].strftime("%m/%d %H:%M"),
            }
            for f in files
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("出力ディレクトリが空です。")

    st.divider()

    # ── 一括実行 ──
    section_title("⏩ 一括実行（ルール抽出 + Excel 出力）")

    if st.button("🏃 一括実行（ルール抽出 → Excel）", use_container_width=True, type="primary"):
        with st.spinner("パイプライン実行中..."):
            success1 = run_rule_pipeline()
            if success1:
                success2 = run_excel_export()
                if success2:
                    st.success("✅ ルール抽出 + Excel 出力 完了！")
                    st.balloons()
                else:
                    st.warning("ルール抽出は成功しましたが、Excel 出力に失敗しました。")
            else:
                st.error("ルール抽出に失敗しました。")
