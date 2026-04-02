from logging import getLogger
from pathlib import Path
from secrets import token_hex

import docker
import docker.errors
from langchain.tools import BaseTool, tool

logger = getLogger(__name__)


class AnalysisContainer:
    MOUNT_DIR: str = "/work/apps"

    def __init__(self, image_tag: str, dockerfile_path: Path):
        self.docker = docker.from_env()
        try:
            self.image = self.docker.images.get(image_tag)
        except docker.errors.ImageNotFound:
            self.image, _ = self.docker.images.build(
                path=str(dockerfile_path.parent),
                dockerfile=str(dockerfile_path.name),
                tag=image_tag,
            )
        self.container = None

    def start(self, input_dir: Path) -> None:
        if self.container is not None:
            return None
        self.container = self.docker.containers.run(
            image=self.image,
            command=["sleep", "infinity"],
            detach=True,
            volumes={str(input_dir): {"bind": self.MOUNT_DIR, "mode": "rw"}},
            name=f"cuttleagent-analysis-{token_hex(4)}",
        )

    def exec(self, command: list[str]) -> str | None:
        if self.container is None:
            logger.warning("Tried to exec non-existent container.")
            return None
        result = self.container.exec_run(command)
        return result.output.decode()

    def stop(self) -> None:
        if self.container is None:
            logger.warning("Tried to stop non-existent container.")
            return None
        self.container.stop()

    def remove(self) -> None:
        if self.container is None:
            logger.warning("Tried to remove non-existent container.")
            return None
        self.container.remove()


def create_analyze_artifact_tool(
    container: AnalysisContainer, description: str
) -> BaseTool:
    @tool(description=description)
    def analyze_artifact(command: list[str]) -> str:
        try:
            result = container.exec(command)
            if result is None:
                raise Exception("Result was None")
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    return analyze_artifact
