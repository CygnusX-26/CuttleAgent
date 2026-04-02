import os
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, cast

from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_tavily import TavilySearch

from src.bug_hunter.prompts import BUG_HUNTER_PROMPT
from src.models import Agent

logger = getLogger(__name__)


class BugHunter:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        model: Agent,
        artifact_analyzer: BaseTool,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir

        tools = []
        tools.append(artifact_analyzer)

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

    def find_cves(self) -> Iterator[dict[str, Any]]:
        user_prompt = (
            f"Analyze the apps in the directory at {self.input_dir}. "
            f"Write REPORT.md in {self.input_dir}/findings."
            f"Write the per-app app_name.md, and poc.md in {self.input_dir}/findings/app_name directory"
            "Process one app at a time, research only known public vulnerabilities."
        )
        inputs = {"messages": [HumanMessage(content=user_prompt)]}

        return self.agent.stream(cast(Any, inputs), stream_mode="updates")
