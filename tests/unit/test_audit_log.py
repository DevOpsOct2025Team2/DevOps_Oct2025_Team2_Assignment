from unittest.mock import patch

from app.audit import log as audit_log


def test_sanitize_log_value_removes_newlines_and_control_chars():
    raw = "alice\r\nadmin\x01"
    sanitized = audit_log._sanitize_log_value(raw)

    assert "\r" not in sanitized
    assert "\n" not in sanitized
    assert "\x01" not in sanitized
    assert "alice" in sanitized
    assert "admin" in sanitized


def test_sanitize_log_value_handles_non_string_values():
    assert audit_log._sanitize_log_value(1234) == "1234"
    assert audit_log._sanitize_log_value(None) == ""


def test_log_admin_action_emits_sanitized_message():
    with patch.object(audit_log.logger, "info") as mock_info:
        audit_log.log_admin_action("admin\nname", "Deleted user\r\nbob")

    mock_info.assert_called_once()
    message = mock_info.call_args.args[0]
    assert "[AUDIT]" in message
    assert "Admin: admin name" in message
    assert "Action: Deleted user  bob" in message
