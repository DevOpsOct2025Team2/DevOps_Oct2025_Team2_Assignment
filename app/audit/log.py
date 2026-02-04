import logging
from datetime import datetime, timezone
# used python modules, timestamps
logger = logging.getLogger(__name__)

# improved fix 
def _sanitize_log_value(value):
    """
    Normalize a value for safe logging by removing control characters
    that could break log formatting (e.g. newlines).
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    # Remove carriage returns and newlines explicitly, and strip other control chars.
    cleaned = value.replace("\r", " ").replace("\n", " ")
    cleaned = "".join(ch for ch in cleaned if ch >= " " or ch == "\t")
    return cleaned

def log_admin_action(admin_username, action):
    timestamp = datetime.now(timezone.utc).isoformat()
    safe_admin = _sanitize_log_value(admin_username)
    safe_action = _sanitize_log_value(action)
    log_message = f"[AUDIT] {timestamp} | Admin: {safe_admin} | Action: {safe_action}"
    logger.info(log_message)