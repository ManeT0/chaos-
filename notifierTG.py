import requests
from datetime import datetime

class Notifier:
    def __init__(self, config):
        self.telegram_token = config.get("telegram_token")
        self.telegram_chat_id = config.get("telegram_chat_id")
        self.slack_webhook = config.get("slack_webhook")
    
    def send(self, message: str, level: str = "info"):
        """Отправляет уведомление во все каналы"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level.upper()}] {message}"
        
        if self.telegram_token:
            self._send_telegram(formatted)
        if self.slack_webhook:
            self._send_slack(formatted)
    
    def _send_telegram(self, message: str):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        requests.post(url, json={
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        })
    
    def _send_slack(self, message: str):
        requests.post(self.slack_webhook, json={"text": message})