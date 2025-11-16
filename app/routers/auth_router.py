from app.database.schemas import UserCreateModel, LoginResponseModel, UserReadModel, UserLoginModel, RefreshTokenRequest
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_async_session
from app.services.auth_services import register, login, refresh_access_token_service

from app.database.schemas import (
    UserCreateModel, 
    LoginResponseModel, 
    UserReadModel, 
    UserLoginModel, 
    RefreshTokenRequest,
    AppErrorResponse,
    ValidationErrorResponse,
)
router = APIRouter(tags=["auth"])

@router.post("/register", 
            response_model = UserReadModel,status_code=status.HTTP_201_CREATED,
            responses={
                status.HTTP_409_CONFLICT: {
                    "model": AppErrorResponse,
                    "description": "Email address or username already exists"
                },
                status.HTTP_422_UNPROCESSABLE_CONTENT: {
                    "model": ValidationErrorResponse,
                    "description": "Validation error"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Database or unexpected error"
                }
            })
async def register_route(
    register_data: UserCreateModel,
    session: AsyncSession = Depends(get_async_session)
): 
    """Create a new user account."""
    return await register(register_data=register_data, session=session)


@router.post("/login",
             response_model = LoginResponseModel,status_code=status.HTTP_200_OK,
             responses={
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Invalid email or password"
                },
                status.HTTP_422_UNPROCESSABLE_CONTENT: {
                    "model": ValidationErrorResponse,
                    "description": "Validation error"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to process login"
                }
            })
async def login_route(
    login_data: UserLoginModel,
    session: AsyncSession = Depends(get_async_session)
):
    """Log in a user and receive access and refresh tokens."""
    return await login(login_data=login_data, session=session)

@router.post("/refresh",
            status_code=status.HTTP_200_OK,
            responses={
                status.HTTP_401_UNAUTHORIZED: {
                    "model": AppErrorResponse,
                    "description": "Invalid, expired, or mismatched refresh token"
                },
                status.HTTP_422_UNPROCESSABLE_CONTENT: {
                    "model": ValidationErrorResponse,
                    "description": "Validation error"
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": AppErrorResponse,
                    "description": "Failed to refresh token"
                }
            })
async def refresh_token_route(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_async_session)
):
    return await refresh_access_token_service(request.refresh_token, session)