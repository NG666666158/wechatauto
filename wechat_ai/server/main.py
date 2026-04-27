from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from wechat_ai.app.service import DesktopAppService
from wechat_ai.server.api import (
    customers_router,
    controls_router,
    conversations_router,
    dashboard_router,
    debug_router,
    environment_router,
    errors_router,
    events_router,
    health_router,
    identity_router,
    knowledge_router,
    logs_router,
    ping_router,
    privacy_router,
    runtime_router,
    shell_router,
    settings_router,
)
from wechat_ai.server.core import ApiError, ErrorCode, fail_response
from wechat_ai.server.services import RuntimeManager
from wechat_ai.server.services.events import EventBus, RuntimeEventRelay


def create_app(
    *,
    desktop_service: DesktopAppService | None = None,
    event_relay_interval_seconds: float = 1.0,
) -> FastAPI:
    shared_desktop_service = desktop_service or DesktopAppService()
    runtime_manager = RuntimeManager(shared_desktop_service)
    event_bus = EventBus()
    event_relay = RuntimeEventRelay()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.desktop_service = shared_desktop_service
        app.state.runtime_manager = runtime_manager
        app.state.event_bus = event_bus
        app.state.event_relay = event_relay
        stop_event = asyncio.Event()
        app.state.event_relay_stop = stop_event

        async def relay_worker() -> None:
            safe_interval = max(float(event_relay_interval_seconds), 0.1)
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=safe_interval)
                except asyncio.TimeoutError:
                    pass
                if stop_event.is_set():
                    break
                try:
                    await asyncio.to_thread(
                        app.state.event_relay.sync,
                        app.state.desktop_service,
                        app.state.event_bus,
                        trace_id="runtime-relay",
                    )
                except Exception:
                    pass

        await asyncio.to_thread(
            event_relay.sync,
            shared_desktop_service,
            event_bus,
            trace_id="startup-relay",
        )
        app.state.event_relay_task = asyncio.create_task(relay_worker())
        try:
            yield
        finally:
            stop_event.set()
            task = getattr(app.state, "event_relay_task", None)
            if task is not None:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    app = FastAPI(title="WeChat AI Local API", version="0.1.0", lifespan=lifespan)
    app.state.desktop_service = shared_desktop_service
    app.state.runtime_manager = runtime_manager
    app.state.event_bus = event_bus
    app.state.event_relay = event_relay

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or uuid4().hex
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return JSONResponse(
            status_code=exc.status_code,
            content=fail_response(
                code=exc.code,
                message=exc.message,
                detail=exc.detail,
                trace_id=trace_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", "")
        return JSONResponse(
            status_code=422,
            content=fail_response(
                code=ErrorCode.REQUEST_INVALID,
                message="Invalid request",
                detail=exc.errors(),
                trace_id=trace_id,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        del exc
        trace_id = getattr(request.state, "trace_id", "")
        return JSONResponse(
            status_code=500,
            content=fail_response(
                code=ErrorCode.UNKNOWN_ERROR,
                message="Internal server error",
                trace_id=trace_id,
            ),
        )

    app.include_router(ping_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(runtime_router, prefix="/api/v1")
    app.include_router(shell_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(debug_router, prefix="/api/v1")
    app.include_router(errors_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(customers_router, prefix="/api/v1")
    app.include_router(controls_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(knowledge_router, prefix="/api/v1")
    app.include_router(logs_router, prefix="/api/v1")
    app.include_router(privacy_router, prefix="/api/v1")
    app.include_router(environment_router, prefix="/api/v1")

    @app.get("/api/v1/debug/error", include_in_schema=False)
    def debug_error(kind: str = Query("api")) -> None:
        if kind == "validation":
            return None
        raise ApiError(
            ErrorCode.CONFIG_INVALID,
            "Debug API error",
            detail={"kind": kind},
            status_code=400,
        )

    return app


app = create_app()
