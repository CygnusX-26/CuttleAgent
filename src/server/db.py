from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from src.server.models import InstanceRecord, InstanceState


class InstanceDb:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._lock = threading.Lock()
        self._connection: sqlite3.Connection | None = None

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self._connection is None:
                self._connection = sqlite3.connect(
                    self._database_path,
                    check_same_thread=False,
                )
                self._connection.row_factory = sqlite3.Row

            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS instances (
                    instance_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    instance_num INTEGER NOT NULL UNIQUE,
                    config_json TEXT NOT NULL,
                    runtime_dir TEXT NOT NULL,
                    launch_command_json TEXT NOT NULL,
                    adb_serial TEXT,
                    webrtc_port INTEGER,
                    expires_at TEXT,
                    failure_reason TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_instances_state
                    ON instances(state);

                CREATE INDEX IF NOT EXISTS idx_instances_expires_at
                    ON instances(expires_at);
                """
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            if self._connection is None:
                return
            self._connection.close()
            self._connection = None

    def upsert(self, record: InstanceRecord) -> None:
        with self._lock:
            connection = self._require_connection()
            connection.execute(
                """
                INSERT INTO instances (
                    instance_id,
                    owner_id,
                    state,
                    instance_num,
                    config_json,
                    runtime_dir,
                    launch_command_json,
                    adb_serial,
                    webrtc_port,
                    expires_at,
                    failure_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instance_id) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    state = excluded.state,
                    instance_num = excluded.instance_num,
                    config_json = excluded.config_json,
                    runtime_dir = excluded.runtime_dir,
                    launch_command_json = excluded.launch_command_json,
                    adb_serial = excluded.adb_serial,
                    webrtc_port = excluded.webrtc_port,
                    expires_at = excluded.expires_at,
                    failure_reason = excluded.failure_reason
                """,
                (
                    record.instance_id,
                    record.owner_id,
                    record.state.value,
                    record.instance_num,
                    record.config.model_dump_json(),
                    record.runtime_dir,
                    json.dumps(record.launch_command),
                    record.adb_serial,
                    record.webrtc_port,
                    record.expires_at.isoformat(),
                    record.failure_reason,
                ),
            )
            connection.commit()

    def get(self, instance_id: str) -> InstanceRecord | None:
        with self._lock:
            connection = self._require_connection()
            row = connection.execute(
                "SELECT * FROM instances WHERE instance_id = ?",
                (instance_id,),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_instances(self) -> list[InstanceRecord]:
        with self._lock:
            connection = self._require_connection()
            rows = connection.execute(
                "SELECT * FROM instances ORDER BY expires_at DESC"
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def delete_instance(self, instance_id: str) -> None:
        with self._lock:
            connection = self._require_connection()
            connection.execute(
                "DELETE FROM instances WHERE instance_id = ?",
                (instance_id,),
            )
            connection.commit()

    def list_active_instance_numbers(self) -> set[int]:
        active_states = (
            InstanceState.STARTING.value,
            InstanceState.ACTIVE.value,
            InstanceState.STOPPING.value,
        )
        placeholders = ", ".join("?" for _ in active_states)
        with self._lock:
            connection = self._require_connection()
            rows = connection.execute(
                f"""
                SELECT instance_num
                FROM instances
                WHERE state IN ({placeholders})
                """,
                active_states,
            ).fetchall()
        return {int(row["instance_num"]) for row in rows}

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("database has not been initialized")
        return self._connection

    def _row_to_record(self, row: sqlite3.Row) -> InstanceRecord:
        return InstanceRecord.model_validate(
            {
                "instance_id": row["instance_id"],
                "owner_id": row["owner_id"],
                "state": row["state"],
                "instance_num": row["instance_num"],
                "config": json.loads(row["config_json"]),
                "runtime_dir": row["runtime_dir"],
                "launch_command": json.loads(row["launch_command_json"]),
                "adb_serial": row["adb_serial"],
                "webrtc_port": row["webrtc_port"],
                "expires_at": row["expires_at"],
                "failure_reason": row["failure_reason"],
            }
        )
