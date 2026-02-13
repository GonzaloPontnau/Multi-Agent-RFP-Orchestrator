import logging
import sys
from functools import lru_cache
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"

FLOW_SYMBOLS = {
    "start": ">>",
    "node": "|",
    "arrow": "->",
    "end": "<<",
    "route": "*",
}


def _configure_root_logger(level: LogLevel) -> None:
    """Configura el logger raiz con handlers de consola y archivo."""
    root = logging.getLogger()
    if root.handlers:
        return

    noisy_loggers = [
        "watchfiles",
        "watchfiles.main",
        "httpx",
        "httpcore",
        "httpcore.http11",
        "httpcore.connection",
        "hpack",
        "urllib3",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    formatter = logging.Formatter(_LOG_FORMAT, _DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    try:
        _LOG_DIR.mkdir(exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            _LOG_DIR / "rfp_orchestrator.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception:
        pass

    root.setLevel(level)


@lru_cache(maxsize=128)
def get_logger(name: str) -> logging.Logger:
    """Retorna un logger configurado para el modulo especificado."""
    from app.core.config import settings

    _configure_root_logger(settings.log_level)
    return logging.getLogger(name)


class AgentLogger:
    """Logger especializado para trazabilidad de agentes LangGraph."""

    def __init__(self, agent_name: str):
        self._logger = get_logger(f"agent.{agent_name}")
        self.agent_name = agent_name

    def pipeline_start(self, question: str, trace_id: str | None = None) -> None:
        """Log inicio del pipeline de agentes."""
        trace_prefix = f"[{trace_id}] " if trace_id else ""
        self._logger.info("=" * 70)
        self._logger.info(f"{trace_prefix}{FLOW_SYMBOLS['start']} PIPELINE START")
        self._logger.info(f"{trace_prefix}{FLOW_SYMBOLS['node']} Question: {question[:100]}{'...' if len(question) > 100 else ''}")
        self._logger.info(
            f"{trace_prefix}{FLOW_SYMBOLS['node']} Flow: START -> retrieve -> grade_and_route -> specialist/quant -> risk_sentinel -> END"
        )
        self._logger.info("=" * 70)

    def pipeline_end(self, state: dict) -> None:
        """Log fin del pipeline con resumen."""
        trace_id = state.get("trace_id")
        trace_prefix = f"[{trace_id}] " if trace_id else ""
        domain = state.get("domain", "N/A")
        docs_total = len(state.get("context", []))
        docs_filtered = len(state.get("filtered_context", []))
        revisions = state.get("revision_count", 0)
        audit = state.get("audit_result", "N/A")
        answer_len = len(state.get("answer", ""))

        self._logger.info("=" * 70)
        self._logger.info(f"{trace_prefix}{FLOW_SYMBOLS['end']} PIPELINE COMPLETE")
        self._logger.info(f"{trace_prefix}   {FLOW_SYMBOLS['route']} Domain Selected: {domain.upper()}")
        self._logger.info(f"{trace_prefix}   {FLOW_SYMBOLS['route']} Specialist Used: specialist_{domain}")
        self._logger.info(f"{trace_prefix}   {FLOW_SYMBOLS['route']} Documents: {docs_total} retrieved -> {docs_filtered} filtered")
        self._logger.info(f"{trace_prefix}   {FLOW_SYMBOLS['route']} Revisions: {revisions} | Audit: {audit}")
        self._logger.info(f"{trace_prefix}   {FLOW_SYMBOLS['route']} Answer Length: {answer_len} chars")
        self._logger.info("=" * 70)

    def node_enter(self, node: str, state: dict | None = None) -> None:
        """Log entrada a nodo."""
        question = state.get("question", "N/A")[:50] if state else "N/A"
        trace_id = state.get("trace_id") if state else None
        trace_prefix = f"[{trace_id}] " if trace_id else ""
        self._logger.debug(f"{trace_prefix}{FLOW_SYMBOLS['node']} [{node.upper()}] {FLOW_SYMBOLS['arrow']} Entering | Q: {question}...")

    def node_exit(self, node: str, result: str | None = None) -> None:
        """Log salida de nodo."""
        self._logger.debug(f"{FLOW_SYMBOLS['node']} [{node.upper()}] {FLOW_SYMBOLS['arrow']} Exiting | {result or 'OK'}")

    def routing_decision(self, from_node: str, to_node: str, reason: str) -> None:
        """Log decision de enrutamiento entre nodos."""
        self._logger.debug(f"{FLOW_SYMBOLS['route']} ROUTING: {from_node} -> {to_node} | Reason: {reason}")

    def specialist_selected(self, domain: str, question: str) -> None:
        """Log seleccion de especialista."""
        self._logger.info(f"{FLOW_SYMBOLS['route']} SPECIALIST SELECTED: specialist_{domain}")
        self._logger.info(f"   |_ Domain '{domain}' best matches question type")

    def error(self, node: str, error: Exception) -> None:
        """Log errores de nodo."""
        self._logger.error(f"{FLOW_SYMBOLS['node']} [{node.upper()}] ERROR: {type(error).__name__}: {error}", exc_info=True)

    def debug(self, node: str, message: str) -> None:
        """Log debug de nodo."""
        self._logger.debug(f"{FLOW_SYMBOLS['node']} [{node}] {message}")
