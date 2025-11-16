import logging
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.db import User, Post, Upvote
from app.database.schemas import UserReadModel, UserUpdateModel, UserDetailResponse, DeletionResponse, CurrentUserResponse
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)


async def get_current_user_service(
    current_user: User,
    session: AsyncSession
):
    try:
        await session.refresh(current_user, ["posts"])
        
        posts_count = len(current_user.posts) if current_user.posts else 0
        
        return CurrentUserResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            total_upvotes=current_user.total_upvotes,
            posts_count=posts_count,
            #created_at=current_user.created_at.isoformat() if current_user.created_at else None
        )

    except Exception as e:
        logger.error(f"Error retrieving current user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )
        
async def get_user_detail(user_id: str, session: AsyncSession) -> UserDetailResponse:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    result = await session.execute(
        select(User)
        .options(selectinload(User.posts))
        .where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        posts_count = len(user.posts) if user.posts else 0
        
        return UserDetailResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            total_upvotes=user.total_upvotes,
            posts_count=posts_count,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
    except Exception as e:
        logger.error(f"Error retrieving user detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details"
        )


async def get_all_users(skip: int = 0, limit: int = 10, session: AsyncSession = None) -> list[UserReadModel]:
    
    if skip < 0 or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters"
        )
    
    if limit > 100:
        limit = 100  # Max limit
    
    try:
        result = await session.execute(
            select(User)
            .offset(skip)
            .limit(limit)
        )
        users = result.scalars().all()
        
        return [
            UserReadModel(
                id=str(user.id),
                email=user.email,
                username=user.username
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error retrieving users list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


async def update_user(user_id: str, update_data: UserUpdateModel, current_user: User, session: AsyncSession) -> UserReadModel:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Authorization check: users can only update their own profile
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You can only update your own profile"
        )
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        update_fields = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_fields.items():
            if value is not None:
                setattr(user, field, value)
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"User updated successfully: {user.id}")
        
        return UserReadModel(
            id=str(user.id),
            email=user.email,
            username=user.username
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


async def delete_user(user_id: str, current_user: User, session: AsyncSession) -> DeletionResponse:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You can only delete your own account"
        )
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        await session.delete(user)
        await session.commit()
        
        logger.info(f"User deleted successfully: {user_id}")
        
        return DeletionResponse(message="User deleted successfully")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


async def get_user_posts(user_id: str, skip: int = 0, limit: int = 10, session: AsyncSession = None) -> list:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    if skip < 0 or limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters"
        )
    
    if limit > 100:
        limit = 100
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        posts_result = await session.execute(
            select(Post)
            .where(Post.user_id == user_uuid)
            .offset(skip)
            .limit(limit)
        )
        posts = posts_result.scalars().all()
        
        return posts
    except Exception as e:
        logger.error(f"Error retrieving user posts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user posts"
        )
