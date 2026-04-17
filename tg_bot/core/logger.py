import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    correlation_id_var.set(cid)


def add_correlation_id(
    logger: Any, method: str, event_dict: dict
) -> dict:
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            add_correlation_id,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
