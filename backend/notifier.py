from datetime import datetime
import requests
import json
import base64
from backend.models import NotificationsConfig

class Notifier:
    def __init__(self, config: NotificationsConfig):
        self.config = config

    def send(self, message: str, level: str = "info", experiment_details: dict = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self.config.telegram.token and self.config.telegram.chat_id:
            self._send_telegram(message, level, timestamp)
        if self.config.slack.webhook:
            self._send_slack(message, level, experiment_details)
        if self.config.teams_webhook:
            self._send_teams(message, level, experiment_details)
        if self.config.pagerduty_routing_key and level in ["error", "critical", "failed"]:
            self._send_pagerduty(message, experiment_details)

        return {"sent": True, "message": message}

    def send_report(self, message: str, html_content: str = None, pdf_bytes: bytes = None):
        if self.config.slack.webhook:
            self._send_slack(f"Report Generated: {message}", level="info")
        if self.config.teams_webhook:
            self._send_teams(f"Report Generated: {message}", level="info")

    def _send_telegram(self, message: str, level: str, timestamp: str):
        url = f"https://api.telegram.org/bot{self.config.telegram.token}/sendMessage"
        html_msg = f"<b>[{level.upper()}]</b> <i>{timestamp}</i>\n<code>{message}</code>"
        try:
            requests.post(
                url,
                json={"chat_id": self.config.telegram.chat_id, "text": html_msg, "parse_mode": "HTML"},
                timeout=5,
            )
        except Exception:
            pass

    def _send_slack(self, message: str, level: str = "info", details: dict = None):
        color = "#36a64f" if level == "info" else "#ff0000"
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{level.upper()}*\n{message}"}
            }
        ]
        if details:
            fields = [{"type": "mrkdwn", "text": f"*{k}*: {v}"} for k, v in details.items()][:10]
            if fields:
                blocks.append({"type": "section", "fields": fields})
                
        try:
            requests.post(self.config.slack.webhook, json={"blocks": blocks}, timeout=5)
        except Exception:
            pass

    def _send_teams(self, message: str, level: str = "info", details: dict = None):
        color = "00FF00" if level == "info" else "FF0000"
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": message,
            "sections": [{
                "activityTitle": message,
                "facts": [{"name": k, "value": str(v)} for k, v in (details or {}).items()]
            }]
        }
        try:
            requests.post(self.config.teams_webhook, json=payload, timeout=5)
        except Exception:
            pass

    def _send_pagerduty(self, message: str, details: dict = None):
        payload = {
            "routing_key": self.config.pagerduty_routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": message,
                "severity": "error",
                "source": "chaos-platform",
                "custom_details": details or {}
            }
        }
        try:
            requests.post("https://events.pagerduty.com/v2/enqueue", json=payload, timeout=5)
        except Exception:
            pass
