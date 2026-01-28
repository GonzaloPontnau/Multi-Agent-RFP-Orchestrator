import logging
import sys
from functools import lru_cache
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger(level: LogLevel) -> None:
    """Configura el logger raíz una sola vez."""
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)


@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger configurado para el módulo especificado.
    
    Uso:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Mensaje")
    """
    from app.core.config import settings
    
    _configure_root_logger(settings.log_level)
    return logging.getLogger(name)


class AgentLogger:
    """Logger especializado para trazabilidad de agentes LangGraph."""

    def __init__(self, agent_name: str):
        self._logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name

    def node_enter(self, node: str, state: dict | None = None) -> None:
        question = state.get("question", "N/A")[:50] if state else "N/A"
        self._logger.info(f"[{node}] >>> Entrando | Question: {question}...")

    def node_exit(self, node: str, result: str | None = None) -> None:
        self._logger.info(f"[{node}] <<< Saliendo | {result or 'OK'}")

    def error(self, node: str, error: Exception) -> None:
        self._logger.error(f"[{node}] ERROR: {type(error).__name__}: {error}", exc_info=True)

    def debug(self, node: str, message: str) -> None:
        self._logger.debug(f"[{node}] {message}")
