import json
from pathlib import Path

import typer

from src.bug_hunter.bug_hunter import BugHunter
from src.models import Agent

app = typer.Typer(
    add_completion=False,
    help="Analyze a challenge directory for APK/native-library version clues and known CVEs.",
)


@app.command()
def main(
    input_dir: Path = typer.Option(
        "apps",
        "--input-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        resolve_path=True,
        help="Directory containing challenge APKs and related artifacts.",
    ),
    output_dir: Path = typer.Option(
        "findings",
        "--output-dir",
        file_okay=False,
        dir_okay=True,
        writable=True,
        resolve_path=True,
        help="Directory where REPORT.md, per-app reports and exploit chains will be written.",
    ),
    model: Agent = typer.Option(
        Agent.GEMINI_3_1_PRO_PREVIEW,
        "--model",
        help="LangChain model identifier to use for the agent.",
    ),
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    hunter = BugHunter(
        challenge_dir=input_dir,
        output_dir=output_dir,
        model=model,
    )

    for chunk in hunter.find_cves():
        print(json.dumps(chunk, default=str), flush=True)


if __name__ == "__main__":
    app()
