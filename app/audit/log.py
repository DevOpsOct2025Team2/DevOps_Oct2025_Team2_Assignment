import logging
from datetime import datetime, timezone
# used python modules, timestamps
logger = logging.getLogger(__name__)

def log_admin_action(admin_username, action):
    timestamp = datetime.now(timezone.utc).isoformat()
    log_message = f"[AUDIT] {timestamp} | Admin: {admin_username} | Action: {action}"
    logger.info(log_message)