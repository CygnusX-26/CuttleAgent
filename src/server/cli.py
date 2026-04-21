from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from src.server.config import CuttlefishSettings
from src.server.models import InstanceRecord


@dataclass(frozen=True, slots=True)
class LaunchResult:
    launch_command: list[str]
    adb_serial: str | None
    webrtc_port: int | None


class CuttlefishCli:
    """Handles spawning Cuttlefish instances."""

    def __init__(self, settings: CuttlefishSettings) -> None:
        self.settings = settings

    def start_instance(self, record: InstanceRecord, selinux: bool) -> LaunchResult:
        runtime_dir = Path(record.runtime_dir)
        runtime_dir.mkdir(parents=True, exist_ok=True)

        command = self._build_launch_command(record, selinux)
        subprocess.run(
            command,
            cwd=runtime_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        return LaunchResult(
            launch_command=command,
            adb_serial=None,
            webrtc_port=None,
        )

    def stop_instance(self, record: InstanceRecord) -> None:
        stop_command = [self.settings.stop_binary]
        if self.settings.stop_binary == "cvd":
            stop_command.append("stop")
        stop_command.append("-instance_num")
        stop_command.append(f"{record.instance_num}")

        subprocess.run(
            stop_command,
            cwd=record.runtime_dir,
            check=True,
            capture_output=True,
            text=True,
        )

    def _build_launch_command(self, record: InstanceRecord, selinux: bool) -> list[str]:
        config = record.config
        command = [self.settings.create_binary]
        if not selinux:
            command.append("-extra_kernel_cmdline")
            command.append("androidboot.selinux=permissive")
        command.extend(
            [
                "-base_instance_num",
                f"{record.instance_num}",
                "-cpus",
                f"{config.cpus}",
                "-start_webrtc",
                f"{config.start_webrtc}",
                "-kernel_path",
                f"{config.kernel_path}",
                "-initramfs_path",
                f"{config.initramfs_path}",
                "-daemon",
                "-report_anonymous_usage_stats=n",
                *config.extra_args,
            ]
        )
        return command
