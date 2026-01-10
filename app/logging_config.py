import logging
import os
import glob
import gzip
import shutil
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

# Try to use structlog if available; otherwise fall back to basic logging
try:
    import structlog  # type: ignore
    STRUCTLOG_AVAILABLE = True
except Exception:
    structlog = None
    STRUCTLOG_AVAILABLE = False

# Optional JSON formatter (handle relocated module to avoid DeprecationWarning)
JsonFormatter = None
JSON_LOGGER_AVAILABLE = False
try:
    # Preferred import location (newer versions)
    from pythonjsonlogger.json import JsonFormatter  # type: ignore
    JSON_LOGGER_AVAILABLE = True
except Exception:
    try:
        # Fallback for older versions
        from pythonjsonlogger import jsonlogger  # type: ignore
        JsonFormatter = getattr(jsonlogger, "JsonFormatter", None)
        JSON_LOGGER_AVAILABLE = JsonFormatter is not None
    except Exception:
        JsonFormatter = None
        JSON_LOGGER_AVAILABLE = False

from app.config import settings


class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        if settings.LOG_COMPRESS:
            # Compress rotated files (skip already compressed)
            for f in glob.glob(self.baseFilename + ".*"):
                if f.endswith(".gz"):
                    continue
                if os.path.isfile(f):
                    with open(f, "rb") as fin, gzip.open(f + ".gz", "wb") as fout:
                        shutil.copyfileobj(fin, fout)
                    try:
                        os.remove(f)
                    except Exception:
                        pass


class CompressingRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        if settings.LOG_COMPRESS:
            # The most recent rotated file is baseFilename + ".1"
            rotated = f"{self.baseFilename}.1"
            if os.path.exists(rotated) and not rotated.endswith(".gz"):
                with open(rotated, "rb") as fin, gzip.open(rotated + ".gz", "wb") as fout:
                    shutil.copyfileobj(fin, fout)
                try:
                    os.remove(rotated)
                except Exception:
                    pass


def _get_formatter():
    if settings.LOG_JSON and JSON_LOGGER_AVAILABLE and JsonFormatter is not None:
        # Use JSON for file logs in production when configured
        return JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    # Fallback human-readable format
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    return logging.Formatter(fmt=fmt, datefmt=datefmt)


def configure_logging():
    """Configure application logging using settings from `app.config.settings`."""

    log_dir = Path(settings.LOG_DIR)
    if not log_dir.is_absolute():
        # make it relative to project root
        log_dir = Path(__file__).resolve().parent.parent / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = _get_formatter()

    root_logger = logging.getLogger()
    # Use configured level
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate logging
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # Console handler (human readable) — keep on console regardless of JSON setting
    console_h = logging.StreamHandler()
    console_h.setLevel(logging.INFO)
    console_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    root_logger.addHandler(console_h)

    # Determine handler classes based on rotation type
    if settings.LOG_ROTATION_TYPE == "time":
        AppHandlerCls = CompressingTimedRotatingFileHandler
        SqlHandlerCls = CompressingTimedRotatingFileHandler
        UvHandlerCls = CompressingTimedRotatingFileHandler
    else:
        AppHandlerCls = CompressingRotatingFileHandler
        SqlHandlerCls = CompressingRotatingFileHandler
        UvHandlerCls = CompressingRotatingFileHandler

    # App log
    app_log_path = str(log_dir / "app.log")
    if settings.LOG_ROTATION_TYPE == "time":
        app_h = AppHandlerCls(app_log_path, when=settings.LOG_ROTATION_WHEN, backupCount=settings.LOG_BACKUP_COUNT)
    else:
        app_h = AppHandlerCls(app_log_path, maxBytes=settings.LOG_MAX_BYTES, backupCount=settings.LOG_BACKUP_COUNT)
    app_h.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    app_h.setFormatter(formatter)
    root_logger.addHandler(app_h)

    # SQLAlchemy logs
    sql_log_path = str(log_dir / "sqlalchemy.log")
    if settings.LOG_ROTATION_TYPE == "time":
        sql_h = SqlHandlerCls(sql_log_path, when=settings.LOG_ROTATION_WHEN, backupCount=settings.LOG_BACKUP_COUNT)
    else:
        sql_h = SqlHandlerCls(sql_log_path, maxBytes=settings.LOG_MAX_BYTES, backupCount=settings.LOG_BACKUP_COUNT)
    sql_h.setLevel(logging.INFO)
    sql_h.setFormatter(formatter)
    sql_logger = logging.getLogger("sqlalchemy.engine")
    for h in list(sql_logger.handlers):
        sql_logger.removeHandler(h)
    sql_logger.setLevel(logging.INFO)
    sql_logger.addHandler(sql_h)
    sql_logger.propagate = False

    # Uvicorn handlers
    access_log_path = str(log_dir / "access.log")
    error_log_path = str(log_dir / "error.log")

    if settings.LOG_ROTATION_TYPE == "time":
        access_h = UvHandlerCls(access_log_path, when=settings.LOG_ROTATION_WHEN, backupCount=settings.LOG_BACKUP_COUNT)
        error_h = UvHandlerCls(error_log_path, when=settings.LOG_ROTATION_WHEN, backupCount=settings.LOG_BACKUP_COUNT)
    else:
        access_h = UvHandlerCls(access_log_path, maxBytes=settings.LOG_MAX_BYTES, backupCount=settings.LOG_BACKUP_COUNT)
        error_h = UvHandlerCls(error_log_path, maxBytes=settings.LOG_MAX_BYTES, backupCount=settings.LOG_BACKUP_COUNT)

    access_h.setLevel(logging.INFO)
    access_h.setFormatter(formatter)
    uv_access_logger = logging.getLogger("uvicorn.access")
    for h in list(uv_access_logger.handlers):
        uv_access_logger.removeHandler(h)
    uv_access_logger.setLevel(logging.INFO)
    uv_access_logger.addHandler(access_h)
    uv_access_logger.propagate = False

    error_h.setLevel(logging.WARNING)
    error_h.setFormatter(formatter)
    uv_error_logger = logging.getLogger("uvicorn.error")
    for h in list(uv_error_logger.handlers):
        uv_error_logger.removeHandler(h)
    uv_error_logger.setLevel(logging.WARNING)
    uv_error_logger.addHandler(error_h)
    uv_error_logger.propagate = False

    # If structlog is available, configure it to use the stdlib logger factory (keep simple)
    if STRUCTLOG_AVAILABLE and structlog is not None:
        structlog.configure(
            processors=[
                structlog.processors.KeyValueRenderer(key_order=["event", "logger", "level"]),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )



# Provide a logger object compatible with structlog or a stdlib logger fallback
if STRUCTLOG_AVAILABLE and structlog is not None:
    logger = structlog.get_logger()
else:
    logger = logging.getLogger("app")

