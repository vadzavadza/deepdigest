from __future__ import annotations

import logging
import sys
from typing import Any

from app.shared.settings import Settings

try:
    import structlog
except ModuleNotFoundError:  # pragma: no cover - fallback for bare environments
    structlog = None  # type: ignore[assignment]


class _PlainLogger:
    def __init__(self, name: str | None = None) -> None:
        self._logger = logging.getLogger(name or 'app')

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info('%s %s', event, kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning('%s %s', event, kwargs)

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception('%s %s', event, kwargs)


def configure_logging(*, settings: Settings) -> None:
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
        level=logging.DEBUG if settings.app_debug else logging.INFO,
    )

    # Keep application debug logs useful without leaking Bot API tokens through
    # verbose httpx/httpcore/python-telegram-bot request dumps. Our own structured
    # search events still stay visible via structlog.
    for noisy_logger in (
        'httpx',
        'httpcore',
        'telegram',
        'telegram.ext',
        'apscheduler',
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    if structlog is None:
        return

    timestamper = structlog.processors.TimeStamper(fmt='iso', utc=False)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            timestamper,
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer('event'),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.app_debug else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None):
    if structlog is None:
        return _PlainLogger(name)
    return structlog.get_logger(name)
