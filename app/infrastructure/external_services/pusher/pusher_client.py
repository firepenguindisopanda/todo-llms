import pusher
from app.config import settings
from typing import Optional, Dict, Any

class PusherService:
    def __init__(self):
        self.pusher_client: Optional[pusher.Pusher] = None
        if all([settings.PUSHER_APP_ID, settings.PUSHER_KEY, settings.PUSHER_SECRET, settings.PUSHER_CLUSTER]):
            self.pusher_client = pusher.Pusher(
                app_id=settings.PUSHER_APP_ID,
                key=settings.PUSHER_KEY,
                secret=settings.PUSHER_SECRET,
                cluster=settings.PUSHER_CLUSTER,
                ssl=True
            )

    def trigger_event(self, channel: str, event_name: str, data: Dict[str, Any]):
        """Triggers a real-time event via Pusher."""
        if self.pusher_client:
            try:
                self.pusher_client.trigger(channel, event_name, data)
                return True
            except Exception as e:
                # Log error or handle it
                print(f"Pusher Error: {e}")
                return False
        return False

    def authenticate_private_channel(self, channel_name: str, socket_id: str):
        """Authenticates a user for a private channel."""
        if self.pusher_client:
            return self.pusher_client.authenticate(
                channel=channel_name,
                socket_id=socket_id
            )
        return None

# Global instance
pusher_service = PusherService()
