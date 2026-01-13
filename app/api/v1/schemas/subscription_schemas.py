from pydantic import BaseModel

class CreateSubscriptionRequest(BaseModel):
    user_id: int
    plan: str

class SubscriptionStatusResponse(BaseModel):
    status: str

class StripeSessionResponse(BaseModel):
    session_id: str
    url: str
