from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, status

from src.server.cli import CuttlefishCli
from src.server.config import CuttlefishSettings
from src.server.db import InstanceDb
from src.server.models import (
    CreateInstanceRequest,
    CreateInstanceResponse,
    InstanceListResponse,
    InstanceView,
    RenewLeaseRequest,
)
from src.server.server_manager import (
    AuthorizationError,
    CapacityError,
    CuttlefishServerManager,
    InstanceError,
    NotFoundError,
)

settings = CuttlefishSettings.from_env()
db = InstanceDb(settings.database_path)
cli = CuttlefishCli(settings)
server_manager = CuttlefishServerManager(settings, db, cli)


@asynccontextmanager
async def lifespan(_: FastAPI):
    server_manager.initialize()
    yield
    db.close()


app = FastAPI(
    title="Cuttlefish Control Plane",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post(
    "/v1/instances",
    response_model=CreateInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_instance(request: CreateInstanceRequest) -> CreateInstanceResponse:
    try:
        return server_manager.create_instance(request)
    except CapacityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except InstanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@app.get("/v1/instances", response_model=InstanceListResponse)
def list_instances() -> InstanceListResponse:
    return server_manager.list_instances()


@app.get("/v1/instances/{instance_id}", response_model=InstanceView)
def get_instance(
    instance_id: str,
    x_lease_token: str | None = Header(default=None),
) -> InstanceView:
    try:
        return server_manager.get_instance(instance_id, x_lease_token)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@app.post("/v1/instances/{instance_id}/renew", response_model=InstanceView)
def renew_instance(
    instance_id: str,
    request: RenewLeaseRequest,
    x_lease_token: str | None = Header(default=None),
) -> InstanceView:
    try:
        return server_manager.renew_lease(instance_id, x_lease_token, request)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@app.post("/v1/instances/{instance_id}/stop", response_model=InstanceView)
def stop_instance(
    instance_id: str,
    x_lease_token: str | None = Header(default=None),
) -> InstanceView:
    try:
        return server_manager.stop_instance(instance_id, x_lease_token)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc
    except InstanceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@app.post("/v1/admin/reconcile", response_model=InstanceListResponse)
def reconcile_expired_instances() -> InstanceListResponse:
    server_manager.reconcile_expired_instances()
    return server_manager.list_instances()
