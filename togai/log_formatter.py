"""JSON log formatter — production'da structured log uchun.

Railway logs view yoki Logtail/Datadog kabi external service'lar
JSON formatdagi loglarni avtomatik parse qiladi.
"""
import json
import logging


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        # Custom extras
        for key in ("request_id", "user_id", "path", "duration_ms"):
            v = getattr(record, key, None)
            if v is not None:
                out[key] = v
        return json.dumps(out, ensure_ascii=False)
