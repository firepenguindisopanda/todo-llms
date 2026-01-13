from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_current_user
from app.infrastructure.database.models.user_model import User as UserModel
from app.application.use_cases.friends.friend_service import FriendService
from app.infrastructure.external_services.pusher.pusher_client import pusher_service
from fastapi.responses import JSONResponse
from app.web.helpers import get_user_from_cookie

router = APIRouter()

@router.post("/pusher/auth")
async def pusher_authentication(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates the user for Pusher private channels."""
    user = await get_user_from_cookie(request, response, db)
    if not user:
         raise HTTPException(status_code=401, detail="Not authenticated")

    form_data = await request.form()
    socket_id = form_data.get("socket_id")
    channel_name = form_data.get("channel_name")

    if not socket_id or not channel_name:
        raise HTTPException(status_code=400, detail="Missing socket_id or channel_name")


    # Security check: Allow subscribing to own private channel or presence-friends
    if not (channel_name == f"private-user-{user.id}" or channel_name == "presence-friends"):
        raise HTTPException(status_code=403, detail="Forbidden: You can only subscribe to your own channel or presence-friends")

    auth = pusher_service.authenticate_private_channel(channel_name, socket_id)
    return JSONResponse(content=auth)


@router.post("/request")
async def send_friend_request(
    request: Request,
    response: Response,
    target: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_user_from_cookie(request, response, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    service = FriendService(db)
    result = await service.send_friend_request(current_user.id, target)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/accept/{request_id}")
async def accept_friend_request(
    request_id: int,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_user_from_cookie(request, response, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = FriendService(db)
    result = await service.accept_friend_request(current_user.id, request_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/reject/{request_id}")
async def reject_friend_request(
    request_id: int,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_user_from_cookie(request, response, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = FriendService(db)
    result = await service.reject_friend_request(current_user.id, request_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.get("/list")
async def list_friends(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_user_from_cookie(request, response, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = FriendService(db)
    friends = await service.list_friends(current_user.id)
    
    # Format response to include online status and public details
    return [
        {
            "id": f.id,
            "username": f.email.split('@')[0], # Simplified username
            "email": f.email if (f.preferences or {}).get("show_email_to_friends", True) else None,
            "is_online": (f.last_seen and (__import__('datetime').datetime.now(__import__('datetime').timezone.utc) - f.last_seen).total_seconds() < 300),
            "last_seen": f.last_seen
        }
        for f in friends
    ]

@router.get("/pending")
async def list_pending_requests(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    current_user = await get_user_from_cookie(request, response, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    service = FriendService(db)
    requests = await service.list_pending_received(current_user.id)
    return [
        {
            "id": r.id,
            "from_user": r.user.email,
            "created_at": r.created_at
        }
        for r in requests
    ]
