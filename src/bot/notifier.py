from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

try:
    from telegram import Bot
except Exception:
    Bot = None  # type: ignore


@dataclass
class Notifier:
    enabled: bool
    token: Optional[str]
    chat_id: Optional[str]

    def send(self, msg: str):
        if not self.enabled or not self.token or not self.chat_id or Bot is None:
            return
        try:
            bot = Bot(token=self.token)
            bot.send_message(chat_id=self.chat_id, text=msg)
        except Exception:
            # Silent fail; logging handled by caller
            pass
