"""
Compose the FastAPI application: middleware, API routes, SPA static files, LLM errors.

``app.py`` exposes ``app = create_app()`` for ``uvicorn app:app``.
"""
from __future__ import annotations

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router as appeal_router
from api.schemas import AppealDraftErrorResponse
from config.logging import configure_logging, get_logger
from config.settings import LOGS_DIR, PROJECT_ROOT
from llm_client import LLMError
from utils.correlation import get_correlation_id, parse_correlation_header
from utils.error_support import format_resolution_for_log

_REACT_DIST = PROJECT_ROOT / "frontend" / "dist"


def create_app() -> FastAPI:
    """
    Build and return the configured FastAPI instance.

    Returns
    -------
    FastAPI
        Application with correlation middleware, ``/api/v1`` routes, ``/health``,
        optional React static mount, and ``LLMError`` → 502 handler.
    """
    load_dotenv()
    configure_logging()
    logger = get_logger("app")

    application = FastAPI(
        title="Appeal Drafter AI",
        description="Draft healthcare denial appeal letters from claim fields; optional payor forms.",
        version="1.0.0",
    )

    logger.info(
        "[E2E] APP_BOOT method=app_factory.create_app react_dist_dir=%s logs_dir=%s",
        _REACT_DIST,
        LOGS_DIR,
    )

    @application.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        request.state.correlation_id = parse_correlation_header(request.headers.get("x-correlation-id"))
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    @application.exception_handler(LLMError)
    async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
        correlation_id = get_correlation_id(request)
        logger.error(
            "[E2E] LLM failure correlation_id=%s message=%s resolution=%s",
            correlation_id,
            exc,
            format_resolution_for_log(getattr(exc, "resolution_steps", ())),
        )
        body = AppealDraftErrorResponse(
            detail=str(exc),
            resolution_steps=list(getattr(exc, "resolution_steps", ()) or ()),
            correlation_id=correlation_id,
            error_type="llm_error",
        )
        return JSONResponse(status_code=502, content=body.model_dump())

    application.include_router(appeal_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    if _REACT_DIST.is_dir() and (_REACT_DIST / "index.html").is_file():
        application.mount(
            "/",
            StaticFiles(directory=str(_REACT_DIST), html=True),
            name="spa",
        )
    else:

        @application.get("/")
        async def ui_not_built() -> PlainTextResponse:
            return PlainTextResponse(
                "UI not built. Run: cd frontend && npm install && npm run build\n"
                "Dev workflow: uvicorn on :8000 + cd frontend && npm run dev (Vite proxies /api).",
                status_code=503,
            )

    return application
