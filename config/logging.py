"""
Application logging: console + rotating file under ``logs/``.

Uses paths and rotation limits from ``config.settings``. All app loggers should use
``get_logger(__name__)`` under the ``appeal_ai`` namespace.

**Execution matches ``app.py`` startup:** ``configure_logging`` runs once at boot;
``get_logger`` is used when modules ask for a named logger.

CLI tools (e.g. ``python -m knowledge_base.ingest``) must call ``configure_logging()`` at
entry so ``appeal_ai.*`` loggers emit to console and file.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import IO, Union

# Use with ``log_console_stream=None`` to omit a console handler (e.g. stdio MCP servers must not log to stdout).
_LOG_CONSOLE_DEFAULT = object()

from config.settings import LOGS_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT

_LOG_FILE = LOGS_DIR / "appeal_drafter.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# --- Step 1: one-time application root logger setup ---


def configure_logging(
    level=logging.INFO,
    log_to_file=True,
    *,
    log_console_stream: Union[IO[str], None, object] = _LOG_CONSOLE_DEFAULT,
) -> None:
    """
    Configure logging for the application. Idempotent; safe to call once at startup.

    Parameters
    ----------
    level : int
        Logging level (default INFO). Use logging.DEBUG for more detail.
    log_to_file : bool
        If True, also write logs to logs/appeal_drafter.log with rotation.
    log_console_stream :
        Stream for the console handler. Default is ``sys.stdout``. Use ``sys.stderr`` for
        processes that reserve stdout (e.g. MCP stdio transport). Use ``None`` to skip the
        console handler (file-only logging).

    Returns
    -------
    None
        Idempotent: no effect if handlers already exist on ``appeal_ai``.
    """
    appeal_ai_root_logger = logging.getLogger("appeal_ai")
    if appeal_ai_root_logger.handlers:
        return
    appeal_ai_root_logger.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    if log_console_stream is _LOG_CONSOLE_DEFAULT:
        stream: IO[str] | None = sys.stdout
    else:
        stream = log_console_stream  # type: ignore[assignment]
    if stream is not None:
        console_handler = logging.StreamHandler(stream)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        appeal_ai_root_logger.addHandler(console_handler)

    if log_to_file:
        try:
            LOGS_DIR.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                str(_LOG_FILE),
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            appeal_ai_root_logger.addHandler(file_handler)
        except OSError:
            appeal_ai_root_logger.warning(
                "Could not create log file at %s; logging to console only.", _LOG_FILE
            )

    for noisy in (
        "httpx",
        "httpcore",
        "openai",
        "google",
        "google.auth",
        "urllib3",
        "uvicorn",
        "uvicorn.access",
        "watchdog",
        "chromadb",
        "chromadb.telemetry",
        "sentence_transformers",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# --- Step 2: child loggers (any time after Step 1) ---


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger under the ``appeal_ai`` hierarchy.

    Parameters
    ----------
    name :
        Typically ``__name__`` from the calling module.

    Returns
    -------
    logging.Logger
        Child logger under ``appeal_ai.*`` (prefix added if missing).
    """
    if not name.startswith("appeal_ai"):
        name = f"appeal_ai.{name}" if name else "appeal_ai"
    return logging.getLogger(name)
