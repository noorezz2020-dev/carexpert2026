import asyncio
from typing import Dict, Set
import json

class NotificationManager:
    def __init__(self):
        self.connections: Dict[str, Set] = {}
    
    async def notify_user(self, user_id: str, message: str, type: str = "info"):
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                try:
                    await ws.send_text(json.dumps({
                        "type": type,
                        "message": message,
                        "timestamp": str(asyncio.get_event_loop().time())
                    }))
                except:
                    pass
    
    async def notify_admin(self, message: str, type: str = "info"):
        await self.notify_user("admin", message, type)

notification_manager = NotificationManager()