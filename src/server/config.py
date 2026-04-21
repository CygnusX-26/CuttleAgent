import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CuttlefishSettings:
    database_path: Path
    runtime_root: Path
    create_binary: str
    stop_binary: str
    remove_binary: str
    instance_timeout_sec: int
    max_instances: int
    challenge_2_kernel_path: Path
    challenge_2_initramfs_path: Path
    challenge_3_kernel_path: Path
    challenge_3_initramfs_path: Path
    challenge_4_kernel_path: Path
    challenge_4_initramfs_path: Path

    @classmethod
    def from_env(cls) -> "CuttlefishSettings":
        return cls(
            database_path=Path(
                os.environ.get("CUTTLEFISH_DB_PATH", "data/cuttlefish.db")
            ),
            runtime_root=Path(
                os.environ.get("CUTTLEFISH_RUNTIME_ROOT", "data/instances")
            ),
            create_binary=os.environ.get("CUTTLEFISH_CREATE_BIN", "cvd"),
            stop_binary=os.environ.get("CUTTLEFISH_STOP_BIN", "cvd"),
            remove_binary=os.environ.get("CUTTLEFISH_REMOVE_BIN", "cvd"),
            instance_timeout_sec=int(
                os.environ.get("CUTTLEFISH_INSTANCE_TIMEOUT_SEC", 600)
            ),
            max_instances=int(os.environ.get("CUTTLEFISH_MAX_INSTANCES", 10)),
            challenge_2_kernel_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_2_KERNEL_PATH", "")
            ),
            challenge_2_initramfs_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_2_INITRAMFS_PATH", "")
            ),
            challenge_3_kernel_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_3_KERNEL_PATH", "")
            ),
            challenge_3_initramfs_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_3_INITRAMFS_PATH", "")
            ),
            challenge_4_kernel_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_4_KERNEL_PATH", "")
            ),
            challenge_4_initramfs_path=Path(
                os.environ.get("CUTTLEFISH_CHALLENGE_4_INITRAMFS_PATH", "")
            ),
        )
