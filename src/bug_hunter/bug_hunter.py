import os
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, cast

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_tavily import TavilySearch

from src.bug_hunter.prompts import ANALYSIS_TOOL_PROMPT, BUG_HUNTER_PROMPT
from src.models import Agent
from src.tools.artifact_analyzer import AnalysisContainer, create_analyze_artifact_tool

logger = getLogger(__name__)


class BugHunter:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        model: Agent,
        dockerfile_path: Path,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        tools = []

        self.analysis_container = AnalysisContainer(
            "cuttlefish_analyzer:latest", dockerfile_path
        )

        analysis_tool = create_analyze_artifact_tool(
            self.analysis_container,
            ANALYSIS_TOOL_PROMPT,
        )

        tools.append(analysis_tool)

        if os.environ.get("TAVILY_API_KEY"):
            tools.append(TavilySearch())
        else:
            raise ValueError(
                "TAVILY_API_KEY not set, TavilySearch tool will not be available."
            )

        self.agent = create_agent(
            model=model.create_agent(),
            tools=tools,
            system_prompt=BUG_HUNTER_PROMPT,
        )

    def run(self) -> None:
        try:
            self.analysis_container.start(self.input_dir, self.output_dir)

            for app in self.analysis_container.list_input_dir():
                BugHunter.stream_output_to_console(self.analyze_app(app))
            BugHunter.stream_output_to_console(self.write_final_report())
        finally:
            self.analysis_container.stop()
            self.analysis_container.remove()

    def analyze_app(self, container_app_path: Path) -> Iterator[dict[str, Any]]:
        user_prompt = f"""Analyze only this APK: {container_app_path}

        Tasks:
        - determine package name and app version
        - enumerate bundled .so files
        - inspect each .so one at a time
        - identify likely library names and version clues
        - research likely known CVEs
        - write findings into {Path(self.analysis_container.OUTPUT_MOUNT) / container_app_path.name / f"{container_app_path.name}.md"}
        - write pocs into {Path(self.analysis_container.OUTPUT_MOUNT) / container_app_path.name / "pocs.md"}

        Do not analyze other apps in this run.
        Do not write REPORT.md in this run.

        """
        inputs = {"messages": [HumanMessage(content=user_prompt)]}

        return self.agent.stream(cast(Any, inputs), stream_mode="updates")

    def write_final_report(self) -> Iterator[dict[str, Any]]:
        user_prompt = f"""
        Read all per-app reports in {self.analysis_container.OUTPUT_MOUNT} and write REPORT.md.

        Tasks:
        - summarize highest-confidence findings
        - note repeated vulnerable components
        - note cross-app observations
        - do not redo raw APK analysis
        - note as many possible chains as you can. (For example an app may call another app with an intent).
        """

        inputs = {"messages": [HumanMessage(content=user_prompt)]}

        return self.agent.stream(cast(Any, inputs), stream_mode="updates")

    @staticmethod
    def stream_output_to_console(stream: Iterator[dict[str, Any]]) -> None:
        for chunk in stream:
            for _, node_update in chunk.items():
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
