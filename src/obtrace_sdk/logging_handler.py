from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ObtraceClient

LEVEL_MAP = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "fatal",
}


class ObtraceLoggingHandler(logging.Handler):
    def __init__(self, client: ObtraceClient, level: int = logging.DEBUG):
        super().__init__(level)
        self._client = client

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = LEVEL_MAP.get(record.levelno, "info")
            message = self.format(record)
            self._client.log(level, message)
        except Exception:
            self.handleError(record)


def install_logging_hook(client: ObtraceClient, level: int = logging.DEBUG) -> ObtraceLoggingHandler:
    handler = ObtraceLoggingHandler(client, level)
    logging.root.addHandler(handler)
    return handler
