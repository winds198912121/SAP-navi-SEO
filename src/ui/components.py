"""
JP Recruit Extractor — Web UI 共通コンポーネント

メトリクスカード、プログレスバー、スタイル定義などの再利用部品。
"""

from __future__ import annotations

import streamlit as st


# ── CSS スタイル ──

CSS = """
<style>
/* 全体フォント */
.stApp {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans",
                 "Yu Gothic", sans-serif;
}

/* メトリクスカード */
.metric-card {
    background: #1a1a2e;
    border-radius: 12px;
    padding: 1.2rem 1rem;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
    transition: transform 0.15s;
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(100,149,237,0.4);
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
    color: #e0e0ff;
    line-height: 1.3;
}
.metric-card .label {
    font-size: 0.8rem;
    color: #8890a0;
    margin-top: 0.2rem;
}
.metric-card.green .value { color: #4ade80; }
.metric-card.yellow .value { color: #facc15; }
.metric-card.red .value { color: #f87171; }

/* 拡張カード */
.detail-card {
    background: #16213e;
    border-radius: 10px;
    padding: 1.5rem;
    border: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 1rem;
}
.detail-card h4 {
    color: #93c5fd;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 0.3rem 0;
}
.detail-card .field-value {
    color: #e2e8f0;
    font-size: 0.95rem;
    line-height: 1.5;
}

/* タグバッジ */
.tag {
    display: inline-block;
    background: rgba(59,130,246,0.15);
    color: #93c5fd;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    font-size: 0.8rem;
    margin: 0.15rem;
    white-space: nowrap;
}
.tag.green { background: rgba(74,222,128,0.15); color: #4ade80; }
.tag.yellow { background: rgba(250,204,21,0.15); color: #facc15; }

/* ステータスバッジ */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
}
.status-badge.ok { background: rgba(74,222,128,0.15); color: #4ade80; }
.status-badge.warn { background: rgba(250,204,21,0.15); color: #facc15; }
.status-badge.bad { background: rgba(248,113,113,0.15); color: #f87171; }

/* セクション区切り */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}

/* フッター */
.footer {
    text-align: center;
    padding: 2rem 0 1rem 0;
    color: #475569;
    font-size: 0.75rem;
}
</style>
"""


def apply_css():
    """カスタム CSS を適用。"""
    st.markdown(CSS, unsafe_allow_html=True)


def metric_card(value: str, label: str, color: str = "normal", help_text: str = ""):
    """メトリクスカードを表示。"""
    color_class = {"green": "green", "yellow": "yellow", "red": "red"}.get(color, "")
    help_attr = f' title="{help_text}"' if help_text else ""
    st.markdown(
        f'<div class="metric-card {color_class}"{help_attr}>'
        f'<div class="value">{value}</div>'
        f'<div class="label">{label}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def detail_field(label: str, value: str | list[str], col=None):
    """詳細カード内のフィールド値。"""
    html = f'<h4>{label}</h4>'
    if isinstance(value, list) and value:
        html += '<div class="field-value">'
        html += "".join(f'<span class="tag">{v}</span>' for v in value)
        html += "</div>"
    elif value:
        html += f'<div class="field-value">{value}</div>'
    else:
        html += '<div class="field-value" style="color: #64748b;">—</div>'

    if col:
        col.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def section_title(title: str):
    """セクションタイトル。"""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def status_badge(text: str, color: str = "ok"):
    """ステータスバッジ。"""
    st.markdown(
        f'<span class="status-badge {color}">{text}</span>',
        unsafe_allow_html=True,
    )


def coverage_color(pct: float) -> str:
    """カバー率に応じた色。"""
    if pct >= 80:
        return "green"
    elif pct >= 50:
        return "yellow"
    return "red"


def footer():
    """フッターを表示。"""
    st.markdown(
        '<div class="footer">JP Recruit Extractor &mdash; '
        "日本招聘案件データ抽出システム</div>",
        unsafe_allow_html=True,
    )
