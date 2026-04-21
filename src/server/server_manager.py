from __future__ import annotations

import hashlib
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from src.server.cli import CuttlefishCli
from src.server.config import CuttlefishSettings
from src.server.db import InstanceDb
from src.server.models import (
    CreateInstanceRequest,
    CreateInstanceResponse,
    InstanceListResponse,
    InstanceRecord,
    InstanceState,
    InstanceView,
    LaunchProfile,
    RenewLeaseRequest,
    ResolvedLaunchConfig,
    utc_now,
)


class InstanceError(Exception):
    pass


class NotFoundError(InstanceError):
    pass


class AuthorizationError(InstanceError):
    pass


class CapacityError(InstanceError):
    pass


@dataclass(frozen=True, slots=True)
class ProfilePreset:
    cpus: int
    selinux: bool
    start_webrtc: bool
    kernel_path: Path | None
    initramfs_path: Path | None
    extra_args: tuple[str, ...] = ()


class CuttlefishServerManager:
    """Manages starting and stopping instances and writing to the db."""

    def __init__(
        self,
        settings: CuttlefishSettings,
        db: InstanceDb,
        cli: CuttlefishCli,
    ) -> None:
        self.settings = settings
        self.db = db
        self.cli = cli
        self.lock = threading.Lock()
        self.profiles: dict[LaunchProfile, ProfilePreset] = {
            LaunchProfile.DEFAULT: ProfilePreset(
                cpus=1,
                selinux=True,
                start_webrtc=True,
                kernel_path=None,
                initramfs_path=None,
            ),
            LaunchProfile.CHALLENGE_2: ProfilePreset(
                cpus=6,
                selinux=False,
                start_webrtc=True,
                kernel_path=self.settings.challenge_2_kernel_path,
                initramfs_path=self.settings.challenge_2_initramfs_path,
            ),
            LaunchProfile.CHALLENGE_3: ProfilePreset(
                cpus=6,
                selinux=False,
                start_webrtc=True,
                kernel_path=self.settings.challenge_3_kernel_path,
                initramfs_path=self.settings.challenge_3_initramfs_path,
            ),
            LaunchProfile.CHALLENGE_4: ProfilePreset(
                cpus=6,
                selinux=False,
                start_webrtc=True,
                kernel_path=self.settings.challenge_4_kernel_path,
                initramfs_path=self.settings.challenge_4_initramfs_path,
            ),
        }

    def initialize(self) -> None:
        self.settings.runtime_root.mkdir(parents=True, exist_ok=True)
        self.db.initialize()

    def create_instance(
        self,
        request: CreateInstanceRequest,
    ) -> CreateInstanceResponse:
        self.reconcile_expired_instances()
        config = self._resolve_config(request)
        now = utc_now()
        expires_at = now + timedelta(seconds=self.settings.instance_timeout_sec)

        with self.lock:
            instance_num = self._allocate_instance_number()
            instance_id = str(uuid.uuid4())
            record = InstanceRecord(
                instance_id=instance_id,
                owner_id=request.owner_id,
                state=InstanceState.STARTING,
                instance_num=instance_num,
                config=config,
                runtime_dir=str(self.settings.runtime_root / instance_id),
                launch_command=[],
                adb_serial=None,
                webrtc_port=None,
                expires_at=expires_at,
                failure_reason=None,
            )
            self.db.upsert(record)

        try:
            launch_result = self.cli.start_instance(record)
        except Exception as exc:
            record.state = InstanceState.CRASHED
            record.failure_reason = str(exc)
            self.db.upsert(record)
            raise InstanceError(f"failed to start instance: {exc}") from exc

        record.launch_command = launch_result.launch_command
        record.adb_serial = launch_result.adb_serial
        record.webrtc_port = launch_result.webrtc_port
        record.state = InstanceState.ACTIVE
        self.db.upsert(record)

        return CreateInstanceResponse(instance=InstanceView.from_record(record))

    def get_instance(self, instance_id: str, lease_token: str | None) -> InstanceView:
        del lease_token
        record = self._get_instance_record(instance_id)
        if record.is_expired(
            now=utc_now(), timeout_sec=self.settings.instance_timeout_sec
        ):
            self._expire_instance(record)
            record = self._get_instance_record(instance_id)
        return InstanceView.from_record(record)

    def renew_lease(
        self,
        instance_id: str,
        lease_token: str | None,
        request: RenewLeaseRequest,
    ) -> InstanceView:
        del lease_token
        record = self._get_instance_record(instance_id)
        timeout_sec = request.timeout_sec or self.settings.instance_timeout_sec
        record.expires_at = utc_now() + timedelta(seconds=timeout_sec)
        self.db.upsert(record)
        return InstanceView.from_record(record)

    def stop_instance(
        self,
        instance_id: str,
        lease_token: str | None,
    ) -> InstanceView:
        del lease_token
        record = self._get_instance_record(instance_id)
        if record.state in {InstanceState.STOPPED, InstanceState.EXPIRED}:
            return InstanceView.from_record(record)

        record.state = InstanceState.STOPPING
        self.db.upsert(record)

        try:
            self.cli.stop_instance(record)
            record.state = InstanceState.STOPPED
            record.failure_reason = None
        except Exception as exc:
            record.state = InstanceState.CRASHED
            record.failure_reason = str(exc)
            self.db.upsert(record)
            raise InstanceError(f"failed to stop instance: {exc}") from exc

        self.db.upsert(record)
        return InstanceView.from_record(record)

    def list_instances(self) -> InstanceListResponse:
        return InstanceListResponse(
            instances=[
                InstanceView.from_record(record) for record in self.db.list_instances()
            ]
        )

    def reconcile_expired_instances(self) -> None:
        for record in self.db.list_instances():
            if record.state in {
                InstanceState.STOPPED,
                InstanceState.EXPIRED,
                InstanceState.CRASHED,
            }:
                continue
            if record.is_expired(
                now=utc_now(), timeout_sec=self.settings.instance_timeout_sec
            ):
                self._expire_instance(record)

    def _expire_instance(self, record: InstanceRecord) -> None:
        try:
            self.cli.stop_instance(record)
        except Exception as exc:
            record.state = InstanceState.CRASHED
            record.failure_reason = f"expire cleanup failed: {exc}"
            self.db.upsert(record)
            return

        record.state = InstanceState.EXPIRED
        self.db.upsert(record)

    def _get_instance_record(self, instance_id: str) -> InstanceRecord:
        record = self.db.get(instance_id)
        if not record:
            raise NotFoundError(f"instance {instance_id} does not exist")
        return record

    def _allocate_instance_number(self) -> int:
        active_numbers = self.db.list_active_instance_numbers()
        for instance_num in range(1, self.settings.max_instances + 1):
            if instance_num not in active_numbers:
                return instance_num
        raise CapacityError(
            f"no instance slots available; max is {self.settings.max_instances}"
        )

    def _resolve_config(self, request: CreateInstanceRequest) -> ResolvedLaunchConfig:
        preset = self.profiles[request.profile]
        kernel_path = (
            request.kernel_path
            if request.profile == LaunchProfile.DEFAULT
            else preset.kernel_path
        )
        initramfs_path = (
            request.initramfs_path
            if request.profile == LaunchProfile.DEFAULT
            else preset.initramfs_path
        )

        if kernel_path is None or initramfs_path is None:
            raise InstanceError(
                f"profile {request.profile.value} is missing kernel/initramfs configuration"
            )

        extra_args = [*preset.extra_args, *request.overrides.extra_args]
        return ResolvedLaunchConfig(
            profile=request.profile,
            cpus=request.overrides.cpus or preset.cpus,
            selinux=(
                request.overrides.selinux
                if request.overrides.selinux is not None
                else preset.selinux
            ),
            start_webrtc=(
                request.overrides.start_webrtc
                if request.overrides.start_webrtc is not None
                else preset.start_webrtc
            ),
            kernel_path=kernel_path,
            initramfs_path=initramfs_path,
            extra_args=extra_args,
        )

    @staticmethod
    def _hash_token(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
