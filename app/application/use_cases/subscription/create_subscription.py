from typing import Dict, Any

class CreateSubscriptionUseCase:
    def __init__(self, payment_service):
        self.payment_service = payment_service

    def execute(self, user_id: int, plan: str) -> Dict[str, Any]:
        """Initiate Stripe Checkout session for subscription."""
        return self.payment_service.create_checkout_session(user_id, plan)
