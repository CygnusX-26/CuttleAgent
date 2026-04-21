import logging
from pathlib import Path

import typer
from dotenv import load_dotenv

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
        resolve_path=True,
        help="Directory for output reports, pocs, and exploits.",
    ),
    bug_hunter_dockerfile: Path = typer.Option(
        "bug_hunter.Dockerfile",
        "--bug-hunter-dockerfile",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Dockerfile to run commands in.",
    ),
    model: Agent = typer.Option(
        Agent.GPT_5_1,
        "--model",
        help="LangChain model identifier to use for the agent.",
    ),
) -> None:
    load_dotenv()
    logging.basicConfig(level=logging.WARNING)

    output_dir.mkdir(parents=True, exist_ok=True)

    # run the bug hunter
    bug_hunter = BugHunter(
        input_dir=input_dir,
        output_dir=output_dir,
        model=model,
        dockerfile_path=bug_hunter_dockerfile,
    )

    bug_hunter.run()

    # run the exploit writer

    # run the exploit chainer


if __name__ == "__main__":
    app()
