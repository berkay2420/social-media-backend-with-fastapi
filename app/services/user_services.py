import logging
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database.db import User, Post
from app.database.schemas import (
    UserReadModel, 
    UserUpdateModel, 
    UserDetailResponse, 
    DeletionResponse, 
    CurrentUserResponse, 
    PostResponseModel,
    UserReadModel as UserReadSchema # Alias to avoid confusion
)
from app.exception_utils import AppException 
from app.exception_utils import (              
    USER_NOT_FOUND, 
    INVALID_USER_ID_FORMAT, 
    PERMISSION_DENIED,
    INTERNAL_SERVER_ERROR,
    INVALID_PAGINATION
)

logger = logging.getLogger(__name__)

async def get_current_user_service(
    current_user: User,
    session: AsyncSession
):
    try:
        
        count_query = select(func.count()).select_from(Post).where(Post.user_id == current_user.id)
        result = await session.execute(count_query)
        posts_count = result.scalar_one()
        
        return CurrentUserResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            total_upvotes=current_user.total_upvotes,
            posts_count=posts_count,
        )

    except Exception as e:
        logger.error(f"Error retrieving current user: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )
        
async def get_user_detail(user_id: str, current_user: User, session: AsyncSession) -> UserDetailResponse:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
            error_code=INVALID_USER_ID_FORMAT
        )
        
    # Logic check: usually admins view details, or users view themselves. 
    # If you want public profiles, remove this check.
    if str(current_user.id) != user_id and not current_user.is_superuser:
        
        pass 
        # If profiles are public, remove the Exception below:
        # raise AppException(
        #     status_code=status.HTTP_403_FORBIDDEN,
        #     detail="Permission denied.",
        #     error_code=PERMISSION_DENIED
        # )
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code=USER_NOT_FOUND
        )
    
    try:
        
        count_query = select(func.count()).select_from(Post).where(Post.user_id == user_uuid)
        count_res = await session.execute(count_query)
        posts_count = count_res.scalar_one()
        
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
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user details",
            error_code=INTERNAL_SERVER_ERROR
        )


async def get_all_users(skip: int = 0, limit: int = 10, session: AsyncSession = None) -> list[UserReadModel]:
    
    if skip < 0 or limit < 1:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
            error_code=INVALID_PAGINATION
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
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
            error_code=INTERNAL_SERVER_ERROR
        )


async def update_user(user_id: str, update_data: UserUpdateModel, current_user: User, session: AsyncSession) -> UserReadModel:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
            error_code=INVALID_USER_ID_FORMAT
        )
    
    # Authorization check: users can only update their own profile
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You can only update your own profile",
            error_code=PERMISSION_DENIED
        )
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code=USER_NOT_FOUND
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
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
            error_code=INTERNAL_SERVER_ERROR
        )


async def delete_user(user_id: str, current_user: User, session: AsyncSession) -> DeletionResponse:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
            error_code=INVALID_USER_ID_FORMAT
        )
    
    
    if str(current_user.id) != user_id and not current_user.is_superuser:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You can only delete your own account",
            error_code=PERMISSION_DENIED
        )
    
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code=USER_NOT_FOUND
        )
    
    try:
        await session.delete(user)
        await session.commit()
        
        logger.info(f"User deleted successfully: {user_id}")
        
        return DeletionResponse(message="User deleted successfully")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
            error_code=INTERNAL_SERVER_ERROR
        )


async def get_user_posts(user_id: str, skip: int = 0, limit: int = 10, session: AsyncSession = None) -> list[PostResponseModel]:
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
            error_code=INVALID_USER_ID_FORMAT
        )
    
    if skip < 0 or limit < 1 or limit > 100:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
            error_code=INVALID_PAGINATION
        )
    
    # Check User exists
    result = await session.execute(
        select(User).where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code=USER_NOT_FOUND
        )
    
    try:
        
        posts_result = await session.execute(
            select(Post)
            .options(
                selectinload(Post.user)
            )
            .where(Post.user_id == user_uuid)
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        posts = posts_result.scalars().all()
        
        if not posts:  
            return []  
        
        # Map manually to handle missing schema fields (comments=[])
        response = []
        for post in posts:
            response.append(
                PostResponseModel(
                    id=str(post.id),
                    user_id=str(post.user_id),
                    caption=post.caption,
                    url=post.url,
                    file_type=post.file_type,
                    title=post.title,
                    created_at=post.created_at.isoformat(),
                    is_owner=True, 
                    is_upvoted_by_me=False, # Cannot compute without viewer ID context
                    upvote_count=post.upvote_count,
                    comment_count=post.comment_count,
                    user_info=UserReadSchema(
                        id=str(user.id),
                        email=user.email,
                        username=user.username
                    ),
                    comments=[] # Profile feed does not show comments
                )
            )

        return response
    
    except Exception as e:
        logger.error(f"Error retrieving user posts: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user posts",
            error_code=INTERNAL_SERVER_ERROR
        )