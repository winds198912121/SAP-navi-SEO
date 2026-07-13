#!/usr/bin/env python3
"""
JP Recruit Extractor — Web UI メインエントリ

Streamlit マルチページアプリ。以下のページを提供:
- 📊 ダッシュボード: 品質メトリクス一覧
- 📋 案件一覧: 全案件の閲覧・検索・詳細
- 🔄 フィードバックループ: インタラクティブ確認・修正
- 📚 ルール管理: ルールライブラリの閲覧・管理
- ▶️ 実行パネル: パイプライン実行・エクスポート

起動方法:
    streamlit run src/ui/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# src をパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from src.ui.components import apply_css, footer

st.set_page_config(
    page_title="JP Recruit Extractor",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_css()

# ── サイドバーナビゲーション ──

st.sidebar.markdown(
    """
    <div style="text-align:center; margin-bottom:1.5rem;">
        <span style="font-size:2rem;">📋</span>
        <h3 style="margin:0; color:#e2e8f0;">JP Recruit<br>Extractor</h3>
        <p style="font-size:0.75rem; color:#64748b;">日本招聘案件データ抽出</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.divider()

PAGES = {
    "📊 ダッシュボード": "pages/01_Dashboard",
    "📋 案件一覧": "pages/02_Cases",
    "🔄 フィードバック": "pages/03_Feedback",
    "📚 ルール管理": "pages/04_Rules",
    "▶️ 実行パネル": "pages/05_Run",
}

page = st.sidebar.radio("メニュー", list(PAGES.keys()), label_visibility="collapsed")

st.sidebar.divider()

# クイック情報
st.sidebar.markdown("#### クイック起動")
st.sidebar.code("streamlit run src/ui/app.py", language="bash")
st.sidebar.markdown(
    f'<p style="font-size:0.7rem; color:#64748b;">'
    f"プロジェクト: {Path(__file__).resolve().parent.parent.parent.name}</p>",
    unsafe_allow_html=True,
)

st.sidebar.divider()

# バージョン情報
st.sidebar.markdown(
    '<p style="font-size:0.7rem; color:#475569; text-align:center;">'
    "v1.0 &bull; 2026-07</p>",
    unsafe_allow_html=True,
)

# ── ページルーティング ──

page_module = PAGES[page].replace("/", ".")

try:
    mod = __import__(f"src.ui.{page_module}", fromlist=["render"])
    mod.render()
except ImportError as e:
    st.error(f"ページの読み込みに失敗しました: {e}")
    st.info("pip で streamlit と plotly がインストールされているか確認してください。")

footer()
