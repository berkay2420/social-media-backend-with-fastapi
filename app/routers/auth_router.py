from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_async_session, User
from app.auth_dependencies import current_active_user
from app.services.auth_services import register, login, refresh_access_token_service, logout

from app.database.schemas import (
    UserCreateModel, 
    LoginResponseModel, 
    UserReadModel, 
    UserLoginModel, 
    RefreshTokenRequest,
    RefreshTokenResponse,
    AppErrorResponse,
    ValidationErrorResponse,
    DeletionResponse
)

router = APIRouter(tags=["auth"])

@router.post("/register", 
             response_model=UserReadModel,
             status_code=status.HTTP_201_CREATED,
             responses={
                status.HTTP_409_CONFLICT: {"model": AppErrorResponse},
                status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": AppErrorResponse}
             })
async def register_route(
    register_data: UserCreateModel,
    session: AsyncSession = Depends(get_async_session)
): 
    """Create a new user account."""
    return await register(register_data=register_data, session=session)


@router.post("/login",
             response_model=LoginResponseModel,
             status_code=status.HTTP_200_OK,
             responses={
                status.HTTP_401_UNAUTHORIZED: {"model": AppErrorResponse},
                status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ValidationErrorResponse},
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": AppErrorResponse}
             })
async def login_route(
    login_data: UserLoginModel,
    session: AsyncSession = Depends(get_async_session)
):
    """Log in a user and receive access and refresh tokens."""
    return await login(login_data=login_data, session=session)

@router.post("/refresh",
             response_model=RefreshTokenResponse,
             status_code=status.HTTP_200_OK,
             responses={
                status.HTTP_401_UNAUTHORIZED: {"model": AppErrorResponse},
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": AppErrorResponse}
             })
async def refresh_token_route(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Refresh an expired access token using a valid refresh token."""
    return await refresh_access_token_service(request.refresh_token, session)

@router.post(
    "/logout",
    response_model=DeletionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": AppErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": AppErrorResponse}
    }
)
async def logout_route(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Logout user and invalidate refresh token."""
    return await logout(user, session)