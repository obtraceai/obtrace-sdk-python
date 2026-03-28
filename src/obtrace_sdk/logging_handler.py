from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry.instrumentation.logging.handler import LoggingHandler

if TYPE_CHECKING:
    from .client import ObtraceClient


class ObtraceLoggingHandler(LoggingHandler):
    def __init__(self, client: ObtraceClient, level: int = logging.DEBUG):
        super().__init__(
            level=level,
            logger_provider=client._providers.logger_provider,
        )


def install_logging_hook(client: ObtraceClient, level: int = logging.DEBUG) -> ObtraceLoggingHandler:
    handler = ObtraceLoggingHandler(client, level)
    logging.root.addHandler(handler)
    return handler
