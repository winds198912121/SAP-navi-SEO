"""ドキュメント前処理の基底クラス."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.common.models import PreprocessingResult


class DocumentPreprocessor(ABC):
    """ドキュメント前処理の抽象基底クラス。

    各ファイル形式（PDF/Word/Excel/HTML/メール/画像）ごとに
    このクラスを継承して実装する。
    """

    SUPPORTED_FORMATS: set[str] = set()

    @abstractmethod
    def process(self, file_path: str | Path) -> PreprocessingResult:
        """ドキュメントを処理し、構造化テキストを返す。

        Args:
            file_path: 入力ファイルのパス

        Returns:
            PreprocessingResult: 処理結果（raw_text, structured_text, metadata等）
        """
        ...

    @abstractmethod
    def detect_encoding(self, file_path: str | Path) -> str:
        """ファイルの文字コードを検出。"""
        ...

    def can_handle(self, file_path: str | Path) -> bool:
        """このプロセッサがファイルを処理できるか判定。"""
        ext = Path(file_path).suffix.lower().lstrip(".")
        return ext in self.SUPPORTED_FORMATS


class PreprocessorPipeline:
    """前処理パイプライン — 適切なプロセッサを選択して実行。"""

    def __init__(self):
        self._processors: dict[str, DocumentPreprocessor] = {}

    def register(self, processor: DocumentPreprocessor) -> None:
        """プロセッサを登録。"""
        for fmt in processor.SUPPORTED_FORMATS:
            self._processors[fmt] = processor

    def process(self, file_path: str | Path) -> PreprocessingResult:
        """ファイルに適したプロセッサで処理。"""
        ext = Path(file_path).suffix.lower().lstrip(".")
        processor = self._processors.get(ext)
        if processor is None:
            return PreprocessingResult(
                error=f"未対応のファイル形式です: .{ext}"
            )
        return processor.process(file_path)
