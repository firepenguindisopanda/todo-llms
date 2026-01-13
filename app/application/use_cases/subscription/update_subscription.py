class UpdateSubscriptionUseCase:
    def __init__(self, payment_service):
        self.payment_service = payment_service

    def execute(self, payload: bytes, sig_header: str):
        """Handle Stripe webhook event to update subscription status."""
        self.payment_service.handle_webhook(payload, sig_header)
