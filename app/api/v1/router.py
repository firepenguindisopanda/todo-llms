from fastapi import APIRouter

from .endpoints import auth, todos, admin, webhooks, subscriptions, friends, chat


router = APIRouter()


router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(todos.router, prefix="/todos", tags=["todos"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(subscriptions.router, tags=["subscriptions"])
router.include_router(webhooks.router, tags=["webhooks"])
router.include_router(friends.router, prefix="/friends", tags=["friends"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
