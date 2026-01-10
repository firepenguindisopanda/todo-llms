from fastapi import APIRouter
from .endpoints import auth, todos, admin

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(todos.router, prefix="/todos", tags=["todos"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
