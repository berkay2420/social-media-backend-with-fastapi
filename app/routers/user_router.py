from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database.db import get_async_session, User
from app.auth_dependencies import current_active_user, require_admin
from app.database.schemas import (
    UserReadModel,
    UserUpdateModel,
    UserDetailResponse,
    DeletionResponse,
    CurrentUserResponse
)
from app.services.user_services import (
    get_user_detail,
    get_all_users,
    update_user,
    delete_user,
    get_user_posts,
    get_current_user_service
)

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await get_current_user_service(user, session)

@router.get("/admin/users", response_model=list[UserReadModel])
async def list_users_route(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    return await get_all_users(user, session)


@router.get("/{user_id}", response_model=UserDetailResponse, status_code=status.HTTP_200_OK)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    
    return await get_user_detail(user_id, session)


@router.put("/{user_id}", response_model=UserReadModel, status_code=status.HTTP_200_OK)
async def update_user_route(
    user_id: str,
    update_data: UserUpdateModel,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
   
    return await update_user(user_id, update_data, current_user, session)


@router.delete("/admin/{user_id}", response_model=DeletionResponse, status_code=status.HTTP_200_OK)
async def delete_user_route(
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    
    return await delete_user(user_id, current_user, session)


@router.get("/{user_id}/posts", status_code=status.HTTP_200_OK)
async def get_user_posts_route(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of posts to return"),
    session: AsyncSession = Depends(get_async_session)
):
    
    return await get_user_posts(user_id, skip=skip, limit=limit, session=session)

