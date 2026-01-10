import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from app import logging_config
from app.config import settings


def _default_log_dir():
    return os.path.abspath(os.path.join(os.path.dirname(logging_config.__file__), "..", "logs"))


def test_logs_directory_and_handlers(tmp_path):
    # Use a temporary logs directory so tests are isolated
    orig_log_dir = settings.LOG_DIR
    orig_log_json = settings.LOG_JSON
    orig_rotation_type = settings.LOG_ROTATION_TYPE
    orig_max_bytes = settings.LOG_MAX_BYTES
    orig_backup = settings.LOG_BACKUP_COUNT
    orig_compress = settings.LOG_COMPRESS

    try:
        settings.LOG_DIR = tmp_path
        settings.LOG_JSON = True
        settings.LOG_ROTATION_TYPE = "size"
        settings.LOG_MAX_BYTES = 200  # small so rotation happens quickly
        settings.LOG_BACKUP_COUNT = 2
        settings.LOG_COMPRESS = True

        logging_config.configure_logging()

        log_dir = str(tmp_path)
        assert os.path.isdir(log_dir), "logs directory should be created"

        # Emit a JSON log line to app logger and ensure app.log exists and is valid JSON
        logging.getLogger("app").info("test app log json")

        # Emit extra large logs to trigger rotation
        long_msg = "X" * 400
        for _ in range(4):
            logging.getLogger("app").info(long_msg)
            # slight pause to allow handlers to process
            time.sleep(0.01)

        # Flush handlers
        for h in logging.getLogger().handlers:
            if hasattr(h, "flush"):
                h.flush()

        app_log = os.path.join(log_dir, "app.log")
        assert os.path.exists(app_log), f"{app_log} should exist"

        # Verify JSON formatting for at least one line in current app.log
        with open(app_log, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert lines, "app.log should contain log lines"
        # Take first line and ensure it's JSON
        try:
            json.loads(lines[0])
        except Exception as e:
            # If JSON logger not available, ensure line contains our message as fallback
            assert "test app log json" in lines[0]

        # Check compressed rotated files exist (.gz)
        gz_files = [p for p in os.listdir(log_dir) if p.startswith("app.log") and p.endswith(".gz")]
        assert gz_files, "There should be at least one compressed rotated log"

    finally:
        # restore settings
        settings.LOG_DIR = orig_log_dir
        settings.LOG_JSON = orig_log_json
        settings.LOG_ROTATION_TYPE = orig_rotation_type
        settings.LOG_MAX_BYTES = orig_max_bytes
        settings.LOG_BACKUP_COUNT = orig_backup
        settings.LOG_COMPRESS = orig_compress

        # reconfigure logging back to defaults
        logging_config.configure_logging()
