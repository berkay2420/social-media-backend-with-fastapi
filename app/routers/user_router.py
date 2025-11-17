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
    CurrentUserResponse,
    ValidationErrorResponse,
    AppErrorResponse,
    PostResponseModel
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

@router.get("/me", response_model=CurrentUserResponse,
            responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to retrieve user profile"
        }
    })
async def get_current_user(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get the profile details for the currently authenticated user."""
    return await get_current_user_service(user, session)

@router.get("/admin/users", response_model=list[UserReadModel],
            responses={
                status.HTTP_400_BAD_REQUEST: {
                    "model": AppErrorResponse,
                    "description": "Invalid pagination parameters"
                },
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Authentication required"
                },
                status.HTTP_403_FORBIDDEN: {
                    "model": AppErrorResponse,
                    "description": "Admin access required"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to retrieve users"
                }
            }
        )
async def list_users_route(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
): 
    """[Admin] Get a paginated list of all users."""
    return await get_all_users(user, session)


@router.get("/admin/{user_id}", response_model=UserDetailResponse, status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_400_BAD_REQUEST: {
                    "model": AppErrorResponse,
                    "description": "Invalid user ID format"
                },
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Authentication required"
                },
                status.HTTP_403_FORBIDDEN: {
                    "model": AppErrorResponse,
                    "description": "Admin access required"
                },
                status.HTTP_404_NOT_FOUND: {
                    "model": AppErrorResponse,
                    "description": "User not found"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to retrieve user details"
                }
            })
async def get_user(
    user_id: str,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """[Admin] Get detailed information for a specific user."""
    return await get_user_detail( user, user_id, session)


@router.put("/{user_id}", response_model=UserReadModel, status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_400_BAD_REQUEST: {
                    "model": AppErrorResponse,
                    "description": "Invalid user ID format"
                },
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Authentication required"
                },
                status.HTTP_403_FORBIDDEN: {
                    "model": AppErrorResponse,
                    "description": "Permission denied"
                },
                status.HTTP_404_NOT_FOUND: {
                    "model": AppErrorResponse,
                    "description": "User not found"
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY: {
                    "model": ValidationErrorResponse,
                    "description": "Validation error"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to update user"
                }
            })
async def update_user_route(
    user_id: str,
    update_data: UserUpdateModel,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Update a user's profile. Users can only update their own profile."""
   
    return await update_user(user_id, update_data, current_user, session)


@router.delete("/admin/{user_id}", response_model=DeletionResponse, status_code=status.HTTP_200_OK,
               responses={
                status.HTTP_400_BAD_REQUEST: {
                    "model": AppErrorResponse,
                    "description": "Invalid user ID format"
                },
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Authentication required"
                },
                status.HTTP_403_FORBIDDEN: {
                    "model": AppErrorResponse,
                    "description": "Admin access required or permission denied"
                },
                status.HTTP_404_NOT_FOUND: {
                    "model": AppErrorResponse,
                    "description": "User not found"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to delete user"
                }
            })
async def delete_user_route(
    user_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """[Admin] Delete a user account."""
    return await delete_user(user_id, current_user, session)


@router.get("/{user_id}/posts", status_code=status.HTTP_200_OK,
            response_model=list[PostResponseModel],
            responses={
                status.HTTP_400_BAD_REQUEST: {
                    "model": AppErrorResponse,
                    "description": "Invalid user ID or pagination"
                },
                status.HTTP_404_NOT_FOUND: {
                    "model": AppErrorResponse,
                    "description": "User not found"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to retrieve user posts"
                }
            }
            )
async def get_user_posts_route(
    user_id: str,
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of posts to return"),
    session: AsyncSession = Depends(get_async_session)
):
    """Get a paginated list of posts from a specific user."""
    return await get_user_posts(user_id, skip=skip, limit=limit, session=session)

