from datetime import datetime

import requests


class Notifier:
    def __init__(self, config: dict | None = None):
        config = config or {}
        telegram = config.get("telegram", {})
        slack = config.get("slack", {})

        self.telegram_token = telegram.get("token") or config.get("telegram_token")
        self.telegram_chat_id = telegram.get("chat_id") or config.get("telegram_chat_id")
        self.slack_webhook = slack.get("webhook") or config.get("slack_webhook")

    def send(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level.upper()}] {message}"

        if self.telegram_token and self.telegram_chat_id:
            self._send_telegram(formatted)
        if self.slack_webhook:
            self._send_slack(formatted)

        return {"sent": True, "message": formatted}

    def _send_telegram(self, message: str):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        requests.post(
            url,
            json={"chat_id": self.telegram_chat_id, "text": message},
            timeout=5,
        )

    def _send_slack(self, message: str):
        requests.post(self.slack_webhook, json={"text": message}, timeout=5)


def send_notification(message: str):
    return Notifier().send(message)
