import os
from logging import getLogger
from pathlib import Path
from typing import Any, Iterator, cast

from langchain.agents import create_agent
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import HumanMessage
from langchain_tavily import TavilySearch

from src.bug_hunter.prompts import BUG_HUNTER_PROMPT
from src.models import Agent
from src.tools.artifact_analyzer import analyze_artifact

logger = getLogger(__name__)


class BugHunter:
    def __init__(self, challenge_dir: Path, output_dir: Path, model: Agent) -> None:
        self.challenge_dir = challenge_dir
        self.output_dir = output_dir

        challenge_dir_toolkit = FileManagementToolkit(
            root_dir=str(challenge_dir), selected_tools=["read_file", "list_directory"]
        )

        output_dir_toolkit = FileManagementToolkit(
            root_dir=str(output_dir), selected_tools=["write_file"]
        )

        tools = []
        tools.extend(challenge_dir_toolkit.get_tools())
        tools.extend(output_dir_toolkit.get_tools())
        tools.append(analyze_artifact)

        if os.environ.get("TAVILY_API_KEY"):
            tools.append(TavilySearch())
        else:
            logger.warning(
                "TAVILY_API_KEY not set, TavilySearch tool will not be available."
            )

        self.agent = create_agent(
            model=model.create_agent(),
            tools=tools,
            system_prompt=BUG_HUNTER_PROMPT,
        )

    def find_cves(self) -> Iterator[dict[str, Any]]:
        user_prompt = (
            f"Analyze the challenge directory at {self.challenge_dir}. "
            f"Write REPORT.md and one Markdown report per app into {self.output_dir}. "
            "Process one app at a time, use local version evidence first, and research "
            "only known public vulnerabilities."
        )
        inputs = {"messages": [HumanMessage(content=user_prompt)]}

        return self.agent.stream(cast(Any, inputs), stream_mode="updates")
