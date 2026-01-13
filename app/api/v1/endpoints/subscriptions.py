from fastapi import APIRouter, Depends, HTTPException
from app.infrastructure.external_services.stripe.stripe_payment_service import StripePaymentService
from app.application.use_cases.subscription.create_subscription import CreateSubscriptionUseCase
from app.application.use_cases.subscription.cancel_subscription import CancelSubscriptionUseCase
from app.application.use_cases.subscription.update_subscription import UpdateSubscriptionUseCase
from app.api.v1.schemas.subscription_schemas import CreateSubscriptionRequest, SubscriptionStatusResponse, StripeSessionResponse
from app.config import settings

router = APIRouter()

stripe_service = StripePaymentService(secret_key=settings.STRIPE_SECRET_KEY or "sk_test")

@router.post("/subscriptions/create-checkout-session", response_model=StripeSessionResponse)
def create_checkout_session(request: CreateSubscriptionRequest):
    use_case = CreateSubscriptionUseCase(stripe_service)
    session = use_case.execute(user_id=request.user_id, plan=request.plan)
    return StripeSessionResponse(**session)

@router.post("/subscriptions/cancel", response_model=SubscriptionStatusResponse)
def cancel_subscription(request: CreateSubscriptionRequest):
    use_case = CancelSubscriptionUseCase(stripe_service)
    use_case.execute(user_id=request.user_id)
    return SubscriptionStatusResponse(status="canceled")

@router.get("/subscriptions/status/{user_id}", response_model=SubscriptionStatusResponse)
def get_subscription_status(user_id: int):
    status = stripe_service.get_subscription_status(user_id)
    return SubscriptionStatusResponse(status=status)
