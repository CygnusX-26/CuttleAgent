import logging
from pathlib import Path

import typer
from dotenv import load_dotenv

from src.bug_hunter.bug_hunter import BugHunter
from src.models import Agent
from src.tools.artifact_analyzer import AnalysisContainer, create_analyze_artifact_tool

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
    dockerfile: Path = typer.Option(
        "Dockerfile",
        "--dockerfile",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help="Dockerfile to run commands in.",
    ),
    model: Agent = typer.Option(
        Agent.GEMINI_2_5_PRO,
        "--model",
        help="LangChain model identifier to use for the agent.",
    ),
) -> None:
    load_dotenv()
    logging.basicConfig(level=logging.WARNING)
    output_dir.mkdir(parents=True, exist_ok=True)

    analysis_container = AnalysisContainer("cuttlefish_analyzer:latest", dockerfile)

    analysis_container.start(input_dir)
    analysis_tool = create_analyze_artifact_tool(
        analysis_container,
        """
        This tool exists to help analyze APK files
        along with all .so files it contains.
        """,
    )

    hunter = BugHunter(
        input_dir=Path(analysis_container.MOUNT_DIR),
        output_dir=output_dir,
        model=model,
        artifact_analyzer=analysis_tool,
    )

    for chunk in hunter.find_cves():
        for node_name, node_update in chunk.items():
            messages = node_update.get("messages", [])
            for message in messages:
                message_type = getattr(message, "type", None)

                if message_type == "ai":
                    if getattr(message, "content", None):
                        print(f"[thought] {message.content}", flush=True)

                    for tool_call in getattr(message, "tool_calls", []) or []:
                        tool_name = tool_call.get("name", "unknown")
                        tool_args = tool_call.get("args", {})
                        print(f"[tool call] {tool_name} {tool_args}", flush=True)

                elif message_type == "tool":
                    tool_name = getattr(message, "name", "unknown")
                    content = getattr(message, "content", "")
                    print(f"[tool result] {tool_name}: {content[:500]}", flush=True)

    analysis_container.stop()
    analysis_container.remove()


if __name__ == "__main__":
    app()
