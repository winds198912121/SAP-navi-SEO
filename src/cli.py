"""コマンドラインインターフェース — CLI エントリーポイント."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from src.common.models import ExtractionMode
from src.config import settings

app = typer.Typer(
    name="jp-extract",
    help="日本招聘案件データ抽出ツール",
    add_completion=False,
)
console = Console()

# ログ設定
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ─────────────────────────────────────────
# メインコマンド: extract
# ─────────────────────────────────────────

@app.command()
def extract(
    input: str = typer.Argument(..., help="入力ファイルパス"),
    output: str = typer.Option(None, "--output", "-o", help="出力ファイルパス"),
    mode: str = typer.Option("auto", "--mode", "-m", help="抽出モード: auto/rule/llm/hybrid"),
    fields: str = typer.Option(None, "--fields", "-f", help="抽出フィールド（カンマ区切り）"),
    pretty: bool = typer.Option(False, "--pretty", "-p", help="整形済みJSONで出力"),
    sandbox: bool = typer.Option(False, "--sandbox", help="Sandbox モード"),
):
    """単一ファイルから案件データを抽出。"""
    file_path = Path(input)
    if not file_path.exists():
        console.print(f"[red]ファイルが見つかりません: {input}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]抽出開始:[/bold] {file_path.name}")
    console.print(f"[dim]モード: {mode}[/dim]")

    # TODO: 実際の抽出パイプラインを呼び出す
    # result = await pipeline.run(file_path, mode=ExtractionMode(mode))

    # 仮の結果
    result = {
        "document_id": "doc_sample_001",
        "extraction_mode": mode,
        "fields": {
            "project_name": {"value": "サンプル案件", "confidence": 0.95, "source": "rule"},
            "skill_requirement": {"value": ["Java", "Python"], "confidence": 0.92, "source": "rule"},
        },
        "metadata": {
            "filename": file_path.name,
            "processing_time_ms": 350,
        },
    }

    # 出力
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2 if pretty else None)
        console.print(f"[green]結果を保存しました: {output_path}[/green]")
    else:
        json_str = json.dumps(result, ensure_ascii=False, indent=2 if pretty else None)
        console.print(json_str)


# ─────────────────────────────────────────
# サブコマンド: batch
# ─────────────────────────────────────────

@app.command()
def batch(
    input_dir: str = typer.Argument(..., help="入力ディレクトリ"),
    output_dir: str = typer.Option("data/output", "--output-dir", "-o", help="出力ディレクトリ"),
    format: str = typer.Option("json", "--format", "-f", help="出力形式: json/csv/excel"),
    workers: int = typer.Option(4, "--workers", "-w", help="並列ワーカー数"),
    skip_existing: bool = typer.Option(False, "--skip-existing", help="既存ファイルをスキップ"),
):
    """複数ファイルを一括抽出。"""
    input_path = Path(input_dir)
    if not input_path.is_dir():
        console.print(f"[red]ディレクトリが見つかりません: {input_dir}[/red]")
        raise typer.Exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # ファイル一覧
    supported_exts = {".pdf", ".docx", ".xlsx", ".html", ".eml", ".png", ".jpg", ".jpeg", ".txt"}
    files = [f for f in input_path.iterdir() if f.suffix.lower() in supported_exts]

    if not files:
        console.print("[yellow]処理可能なファイルが見つかりません[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]{len(files)} 件のファイルを処理します[/bold]")

    with Progress() as progress:
        task = progress.add_task("[green]処理中...", total=len(files))
        for file in files:
            progress.update(task, description=f"[green]処理中: {file.name}")
            # TODO: 実際の抽出処理
            # result = pipeline.run(file, ...)
            progress.advance(task)

    console.print(f"[green]完了! 結果は {output_path} に保存されました[/green]")


# ─────────────────────────────────────────
# サブコマンド: rule
# ─────────────────────────────────────────

@app.group()
def rule():
    """ルールの管理・テスト。"""
    pass


@rule.command("list")
def rule_list(
    field: str = typer.Option(None, "--field", "-f", help="フィールドで絞り込み"),
):
    """ルール一覧を表示。"""
    table = Table(title="ルール一覧")
    table.add_column("Rule ID", style="cyan")
    table.add_column("Field", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", justify="right")
    table.add_column("Accuracy", justify="right")

    # TODO: 実際のルール一覧を取得
    table.add_row("(ルールがありません)", "", "", "", "")

    console.print(table)


@rule.command("show")
def rule_show(
    rule_id: str = typer.Argument(..., help="ルールID"),
):
    """ルール詳細を表示。"""
    console.print(f"[bold]Rule:[/bold] {rule_id}")
    console.print("[yellow]（未実装: ルールリポジトリから取得してください）[/yellow]")


@rule.command("test")
def rule_test(
    rule_id: str = typer.Argument(..., help="ルールID"),
    input: str = typer.Argument(..., help="テスト入力ファイル"),
):
    """ルールをテスト。"""
    console.print(f"[bold]ルールテスト:[/bold] {rule_id}")
    console.print(f"[dim]入力: {input}[/dim]")
    console.print("[yellow]（未実装）[/yellow]")


@rule.command("evaluate")
def rule_evaluate(
    rule_id: str = typer.Argument(..., help="ルールID"),
    test_set: str = typer.Argument(..., help="テストデータセット (.jsonl)"),
):
    """ルールの精度を評価。"""
    console.print(f"[bold]ルール評価:[/bold] {rule_id}")
    console.print("[yellow]（未実装）[/yellow]")


@rule.command("learn")
def rule_learn(
    field: str = typer.Option(None, "--field", "-f", help="学習対象フィールド"),
    format_type: str = typer.Option(None, "--format-type", help="フォーマット種別"),
):
    """ルール学習を手動トリガー。"""
    console.print("[bold]ルール学習を開始します...[/bold]")
    console.print("[yellow]（未実装）[/yellow]")


@rule.command("regression")
def rule_regression(
    test_dir: str = typer.Argument("data/test", help="テストディレクトリ"),
):
    """回帰テストを実行。"""
    console.print("[bold]回帰テスト実行中...[/bold]")
    console.print("[yellow]（未実装）[/yellow]")


# ─────────────────────────────────────────
# サブコマンド: format
# ─────────────────────────────────────────

@app.group()
def format():
    """フォーマット管理。"""
    pass


@format.command("register")
def format_register(
    name: str = typer.Option(..., "--name", "-n", help="フォーマット名"),
    description: str = typer.Option("", "--description", "-d", help="説明"),
    patterns_json: str = typer.Option(None, "--patterns-json", help="識別パターン (JSON)"),
):
    """新フォーマットを登録。"""
    console.print(f"[bold]フォーマット登録:[/bold] {name}")
    console.print("[yellow]（未実装）[/yellow]")


@format.command("list")
def format_list():
    """登録済フォーマット一覧。"""
    table = Table(title="登録フォーマット")
    table.add_column("Format ID", style="cyan")
    table.add_column("Description")
    table.add_column("Samples", justify="right")
    table.add_column("Accuracy", justify="right")

    table.add_row("(フォーマットがありません)", "", "", "")
    console.print(table)


@format.command("stats")
def format_stats(
    name: str = typer.Argument(..., help="フォーマット名"),
):
    """フォーマットの統計情報。"""
    console.print(f"[bold]フォーマット統計:[/bold] {name}")
    console.print("[yellow]（未実装）[/yellow]")


@format.command("review")
def format_review(
    name: str = typer.Argument(..., help="フォーマット名"),
):
    """フォーマットの抽出結果をレビュー。"""
    console.print(f"[bold]レビュー:[/bold] {name}")
    console.print("[yellow]（未実装）[/yellow]")


# ─────────────────────────────────────────
# サブコマンド: stats
# ─────────────────────────────────────────

@app.command()
def stats():
    """システム統計を表示。"""
    table = Table(title="システム統計")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    # TODO: 実際の統計データ
    table.add_row("Total rules", "0")
    table.add_row("Active rules", "0")
    table.add_row("Rule coverage", "0%")
    table.add_row("Avg confidence", "0.0")
    table.add_row("LLM call rate", "0%")
    table.add_row("Processed docs", "0")

    console.print(table)


# ─────────────────────────────────────────
# サブコマンド: feedback
# ─────────────────────────────────────────

@app.group()
def feedback():
    """抽出結果のフィードバック管理。"""
    pass


@feedback.command("list")
def feedback_list(
    status: str = typer.Option("pending", "--status", "-s", help="ステータス: pending/completed"),
):
    """フィードバック一覧。"""
    console.print(f"[bold]フィードバック一覧 ({status})[/bold]")
    console.print("[yellow]（未実装）[/yellow]")


@feedback.command("submit")
def feedback_submit(
    document_id: str = typer.Option(..., "--document-id", help="ドキュメントID"),
    field: str = typer.Option(..., "--field", "-f", help="フィールド名"),
    corrected: str = typer.Option(..., "--corrected", "-c", help="修正値"),
):
    """修正フィードバックを送信。"""
    console.print(f"[bold]フィードバック送信:[/bold] {document_id}")
    console.print("[yellow]（未実装）[/yellow]")


@feedback.command("confirm")
def feedback_confirm(
    document_id: str = typer.Option(..., "--document-id", help="ドキュメントID"),
):
    """抽出結果が正しいことを確認。"""
    console.print(f"[bold]確認送信:[/bold] {document_id}")
    console.print("[yellow]（未実装）[/yellow]")


# ─────────────────────────────────────────
# サブコマンド: init
# ─────────────────────────────────────────

@app.command()
def init():
    """プロジェクトを初期化（ルールDB作成等）。"""
    console.print("[bold]システムを初期化します...[/bold]")

    # 必要なディレクトリを作成
    dirs = [
        settings.rule_db_path.parent,
        settings.cache_dir,
        settings.output_dir,
        settings.sample_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        console.print(f"  [green]✓[/green] {d}")

    console.print("[bold green]初期化完了![/bold green]")


# ─────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────

def main():
    """CLI エントリーポイント。"""
    app()


if __name__ == "__main__":
    main()
