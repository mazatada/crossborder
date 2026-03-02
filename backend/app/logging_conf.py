import logging
import contextvars
from typing import Optional

# contextvar to store the trace_id for the current task/request
trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def get_trace_id() -> Optional[str]:
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> contextvars.Token:
    return trace_id_var.set(trace_id)


def reset_trace_id(token: contextvars.Token) -> None:
    trace_id_var.reset(token)


class TraceIdFilter(logging.Filter):
    """
    Injects the `trace_id` from the contextvar into the LogRecord.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        tid = get_trace_id()
        record.trace_id = tid if tid else "no-trace"
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures the root logger to use the TraceIdFilter and
    a formatter that includes the trace_id.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates during test runs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [TraceID:%(trace_id)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(TraceIdFilter())

    root_logger.addHandler(handler)

    # Optional: Suppress overly verbose logs from third-party libraries if necessary
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
