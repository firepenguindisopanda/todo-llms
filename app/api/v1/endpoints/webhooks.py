from fastapi import APIRouter, Request, Header, Response, Depends
from app.infrastructure.external_services.stripe.stripe_payment_service import StripePaymentService
from app.api.dependencies.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.user_model import User as UserModel
from app.config import settings
import stripe

router = APIRouter()

stripe_service = StripePaymentService(secret_key=settings.STRIPE_SECRET_KEY or "sk_test")

@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db), stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe_service.handle_webhook(payload, stripe_signature)
        
        # Handle 'checkout.session.completed'
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session.get('client_reference_id')
            customer_id = session.get('customer')
            
            if user_id:
                user = await db.get(UserModel, int(user_id))
                if user:
                    user.stripe_customer_id = customer_id
                    user.subscription_status = 'active'
                    await db.commit()
                    
        # Handle 'customer.subscription.deleted' (cancellation)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            
            from sqlalchemy import select
            result = await db.execute(select(UserModel).where(UserModel.stripe_customer_id == customer_id))
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = 'canceled'
                await db.commit()

        # Handle 'customer.subscription.updated'
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            customer_id = subscription.get('customer')
            status = subscription.get('status') # e.g. active, past_due, unpaid, canceled
            
            from sqlalchemy import select
            result = await db.execute(select(UserModel).where(UserModel.stripe_customer_id == customer_id))
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = status
                await db.commit()

        # Handle 'invoice.payment_failed'
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            
            from sqlalchemy import select
            result = await db.execute(select(UserModel).where(UserModel.stripe_customer_id == customer_id))
            user = result.scalar_one_or_none()
            if user:
                user.subscription_status = 'past_due'
                await db.commit()

    except Exception as e:
        import logging
        logging.getLogger("app.api.webhooks").error(f"Webhook error: {e}")
        return Response(status_code=400, content=str(e))
        
    return {"status": "success"}
