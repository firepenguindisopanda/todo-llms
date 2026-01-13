from abc import ABC, abstractmethod
from typing import Any, Dict

class PaymentService(ABC):
    @abstractmethod
    def create_checkout_session(self, user_id: int, plan: str) -> Dict[str, Any]:
        """Create a Stripe Checkout session and return session info."""
        pass

    @abstractmethod
    def handle_webhook(self, payload: bytes, sig_header: str) -> None:
        """Process Stripe webhook events."""
        pass

    @abstractmethod
    def cancel_subscription(self, user_id: int) -> None:
        """Cancel a user's subscription in Stripe."""
        pass

    @abstractmethod
    def get_subscription_status(self, user_id: int) -> str:
        """Get the current subscription status for a user."""
        pass
