"""日本語テキスト正規化モジュール."""

from __future__ import annotations

import re
from typing import ClassVar


class JapaneseTextNormalizer:
    """日本語テキストの標準化パイプライン。

    全半角統一、機種依存文字対応、ルビ除去、改行最適化など。
    """

    # 機種依存文字のマッピング
    KIGOU_MAP: ClassVar[dict[str, str]] = {
        "①": "(1)", "②": "(2)", "③": "(3)", "④": "(4)", "⑤": "(5)",
        "⑥": "(6)", "⑦": "(7)", "⑧": "(8)", "⑨": "(9)", "⑩": "(10)",
        "⑪": "(11)", "⑫": "(12)", "⑬": "(13)", "⑭": "(14)", "⑮": "(15)",
        "⑯": "(16)", "⑰": "(17)", "⑱": "(18)", "⑲": "(19)", "⑳": "(20)",
        "㈱": "(株)", "㈲": "(有)", "㈳": "(社)", "㈵": "(財)",
        "№": "No.", "㏍": "KK", "㏄": "cc",
    }

    # ルビ（振り仮名）除去パターン
    RUBY_PATTERN: ClassVar[re.Pattern] = re.compile(
        r"《[^》]*》|｜[^《\n]*《[^》]*》"
    )

    # 全角英数字→半角
    ZENKAKU_ALPHA: ClassVar[dict[str, str]] = {
        chr(0xFF01 + i): chr(0x21 + i) for i in range(94)
    }

    def normalize(self, text: str, preserve_newlines: bool = False) -> str:
        """完全な正規化パイプラインを実行。

        Args:
            preserve_newlines: True の場合、改行を保持する（構造化テキスト用）
        """
        text = self._unify_width(text)
        text = self._remove_ruby(text)
        text = self._normalize_kigou(text)
        text = self._normalize_punctuation(text)
        if not preserve_newlines:
            text = self._optimize_line_breaks(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    def _unify_width(self, text: str) -> str:
        """全角英数字→半角、半角カナ→全角。"""
        # 全角英数字を半角に
        result = []
        for ch in text:
            code = ord(ch)
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(ch)
        text = "".join(result)

        # 半角カナを全角に
        text = text.replace("ｦ", "ヲ")
        text = text.replace("ｧ", "ァ")
        text = text.replace("ｨ", "ィ")
        text = text.replace("ｩ", "ゥ")
        text = text.replace("ｪ", "ェ")
        text = text.replace("ｫ", "ォ")
        text = text.replace("ｬ", "ャ")
        text = text.replace("ｭ", "ュ")
        text = text.replace("ｮ", "ョ")
        text = text.replace("ｯ", "ッ")
        text = text.replace("ｰ", "ー")
        text = text.replace("ｳﾞ", "ヴ")

        # 半角カナ単文字を全角に（ｱ→ア等）
        HALF_KANA = {
            "ｱ": "ア", "ｲ": "イ", "ｳ": "ウ", "ｴ": "エ", "ｵ": "オ",
            "ｶ": "カ", "ｷ": "キ", "ｸ": "ク", "ｹ": "ケ", "ｺ": "コ",
            "ｻ": "サ", "ｼ": "シ", "ｽ": "ス", "ｾ": "セ", "ｿ": "ソ",
            "ﾀ": "タ", "ﾁ": "チ", "ﾂ": "ツ", "ﾃ": "テ", "ﾄ": "ト",
            "ﾅ": "ナ", "ﾆ": "ニ", "ﾇ": "ヌ", "ﾈ": "ネ", "ﾉ": "ノ",
            "ﾊ": "ハ", "ﾋ": "ヒ", "ﾌ": "フ", "ﾍ": "ヘ", "ﾎ": "ホ",
            "ﾏ": "マ", "ﾐ": "ミ", "ﾑ": "ム", "ﾒ": "メ", "ﾓ": "モ",
            "ﾔ": "ヤ", "ﾕ": "ユ", "ﾖ": "ヨ",
            "ﾗ": "ラ", "ﾘ": "リ", "ﾙ": "ル", "ﾚ": "レ", "ﾛ": "ロ",
            "ﾜ": "ワ", "ｦ": "ヲ", "ﾝ": "ン",
            "ﾞ": "゛", "ﾟ": "゜",
        }
        for half, full in HALF_KANA.items():
            text = text.replace(half, full)

        return text

    def _remove_ruby(self, text: str) -> str:
        """ルビ（振り仮名）を除去。

        パターン:
        - 《...》 → 削除
        - ｜...《...》 → ... 部分だけ残す
        """
        text = self.RUBY_PATTERN.sub("", text)
        return text

    def _normalize_kigou(self, text: str) -> str:
        """機種依存文字を標準化。"""
        for kigou, replacement in self.KIGOU_MAP.items():
            text = text.replace(kigou, replacement)
        return text

    def _normalize_punctuation(self, text: str) -> str:
        """句読点などの約物を統一。"""
        replacements = {
            "．": ".", "。": "。", "、": "、",
            "，": ",", "！": "!", "？": "?",
            "：": ":", "；": ";",
            "（": "(", "）": ")",
            "［": "[", "］": "]",
            "｛": "{", "｝": "}",
            "「": "「", "」": "」",
            "『": "『", "』": "』",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _optimize_line_breaks(self, text: str) -> str:
        """日本語テキストの改行を最適化。

        日本語は単語間で改行されないため、
        句点/読点/閉じ括弧以外での改行をスペースに置換。
        """
        # 改行後の文字が日本語ではない（英単語など）場合はそのまま
        # 句点以外の改行をスペースに
        text = re.sub(r"(?<![。．、）)」】])\n(?!\n)", "", text)
        # 連続改行は段落区切りとして維持
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """空白文字を正規化。"""
        # タブ→スペース
        text = text.replace("\t", " ")
        # 連続スペースを1つに
        text = re.sub(r" {2,}", " ", text)
        return text
