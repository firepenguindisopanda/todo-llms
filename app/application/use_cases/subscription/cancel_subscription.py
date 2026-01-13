class CancelSubscriptionUseCase:
    def __init__(self, payment_service):
        self.payment_service = payment_service

    def execute(self, user_id: int):
        """Cancel the user's subscription in Stripe."""
        self.payment_service.cancel_subscription(user_id)
