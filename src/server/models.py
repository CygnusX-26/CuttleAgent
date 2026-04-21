from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class InstanceState(str, Enum):
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"
    EXPIRED = "expired"


class LaunchProfile(str, Enum):
    DEFAULT = "default"
    CHALLENGE_2 = "challenge_2"
    CHALLENGE_3 = "challenge_3"
    CHALLENGE_4 = "challenge_4"


class LaunchOverrides(BaseModel):
    cpus: int | None = Field(default=None, ge=1, le=64)
    selinux: bool | None = None
    start_webrtc: bool | None = None
    extra_args: list[str] = Field(default_factory=list, max_length=16)


class CreateInstanceRequest(BaseModel):
    owner_id: str = Field(min_length=1, max_length=128)
    profile: LaunchProfile = LaunchProfile.DEFAULT
    kernel_path: Path | None = None
    initramfs_path: Path | None = None
    overrides: LaunchOverrides = Field(default_factory=LaunchOverrides)

    @model_validator(mode="after")
    def validate_launch_source(self) -> "CreateInstanceRequest":
        has_any_explicit_path = (
            self.kernel_path is not None or self.initramfs_path is not None
        )

        if self.profile == LaunchProfile.DEFAULT:
            if self.kernel_path is None or self.initramfs_path is None:
                raise ValueError(
                    "kernel_path and initramfs_path are required when "
                    "profile=default"
                )
        elif has_any_explicit_path:
            raise ValueError(
                "kernel_path and initramfs_path must not be set when using a preset profile"
            )

        return self


class RenewLeaseRequest(BaseModel):
    timeout_sec: int | None = Field(default=None, ge=1)


class ResolvedLaunchConfig(BaseModel):
    profile: LaunchProfile
    cpus: int = Field(ge=1, le=64)
    selinux: bool = False
    start_webrtc: bool = False
    kernel_path: Path
    initramfs_path: Path
    extra_args: list[str] = Field(default_factory=list)


class InstanceRecord(BaseModel):
    instance_id: str
    owner_id: str
    state: InstanceState
    instance_num: int = Field(ge=1)
    config: ResolvedLaunchConfig
    runtime_dir: str
    launch_command: list[str] = Field(default_factory=list)
    adb_serial: str | None = None
    webrtc_port: int | None = None
    expires_at: datetime
    failure_reason: str | None = None

    def is_expired(self, *, now: datetime | None = None, timeout_sec: int) -> bool:
        del timeout_sec
        current_time = now or utc_now()
        return self.expires_at <= current_time


class InstanceView(BaseModel):
    instance_id: str
    owner_id: str
    state: InstanceState
    instance_num: int
    profile: LaunchProfile
    kernel_path: Path
    initramfs_path: Path
    runtime_dir: str
    launch_command: list[str]
    adb_serial: str | None
    webrtc_port: int | None
    expires_at: datetime
    failure_reason: str | None

    @classmethod
    def from_record(cls, record: InstanceRecord) -> "InstanceView":
        return cls(
            instance_id=record.instance_id,
            owner_id=record.owner_id,
            state=record.state,
            instance_num=record.instance_num,
            profile=record.config.profile,
            kernel_path=record.config.kernel_path,
            initramfs_path=record.config.initramfs_path,
            runtime_dir=record.runtime_dir,
            launch_command=record.launch_command,
            adb_serial=record.adb_serial,
            webrtc_port=record.webrtc_port,
            expires_at=record.expires_at,
            failure_reason=record.failure_reason,
        )


class CreateInstanceResponse(BaseModel):
    instance: InstanceView


class InstanceListResponse(BaseModel):
    instances: list[InstanceView]
