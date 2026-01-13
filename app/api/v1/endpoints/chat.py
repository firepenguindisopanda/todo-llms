from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies.database import get_db
from app.web.helpers import get_user_from_cookie
from app.application.use_cases.chat.chat_service import ChatService

router = APIRouter()

@router.post("/send")
async def send_message(
    request: Request,
    response: Response,
    receiver_id: int = Body(..., embed=True),
    content: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_from_cookie(request, response, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    service = ChatService(db)
    message = await service.send_message(user.id, receiver_id, content)
    if not message:
        raise HTTPException(status_code=400, detail="Failed to send message")
    return {"success": True, "message_id": message.id}

@router.get("/history/{friend_id}")
async def get_history(
    friend_id: int,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_from_cookie(request, response, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    service = ChatService(db)
    messages = await service.get_chat_history(user.id, friend_id)
    return [
        {
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "created_at": m.created_at,
            "is_read": m.is_read
        }
        for m in messages
    ]
