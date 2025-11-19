from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import timedelta, datetime, timezone
import logging
import jwt

from app.database.db import User
from app.database.schemas import UserCreateModel, UserLoginModel, UserReadModel, LoginResponseModel, RefreshTokenResponse
from app.utils import verify_password, create_access_token, generate_hash, decode_token, REFRESH_TOKEN_EXPIRY_DAYS
from app.exception_utils import AppException
from app.exception_utils import (
    AUTH_EMAIL_OR_USERNAME_EXISTS,
    AUTH_INVALID_CREDENTIALS,
    AUTH_INVALID_TOKEN,
    AUTH_TOKEN_EXPIRED,
    AUTH_USER_NOT_FOUND_FOR_TOKEN,
    AUTH_TOKEN_MISMATCH,
    INTERNAL_SERVER_ERROR
)

async def register(register_data: UserCreateModel, session: AsyncSession) -> UserReadModel:
    
    hashed_pw = generate_hash(register_data.password)
    
    
    new_user = User(
        email=register_data.email,
        hashed_password=hashed_pw,
        username=register_data.username,
        is_active=True,
        is_verified=False,
    )
    
    session.add(new_user)
    
    try:
        await session.commit()
        await session.refresh(new_user)
        
        return UserReadModel(
            id=str(new_user.id),
            email=new_user.email,
            username=new_user.username
        )
        
    except IntegrityError as e:
        await session.rollback()
        logging.warning(f"Registration conflict: {e}")
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address or username already exists",
            error_code=AUTH_EMAIL_OR_USERNAME_EXISTS
        )
    except Exception as e:
        await session.rollback()
        logging.error(f"Registration error: {e}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
            error_code=INTERNAL_SERVER_ERROR
        )

async def login(login_data: UserLoginModel, session: AsyncSession) -> LoginResponseModel:
    email = login_data.email
    password = login_data.password
    
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password",
            error_code=AUTH_INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        # Payload consistency
        user_payload = {'email': user.email, 'user_id': str(user.id)}
        
        access_token = create_access_token(
            user_data=user_payload
        )
        
        refresh_token = create_access_token(
            user_data=user_payload,
            refresh=True,
            expiry=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        )

        user.refresh_token = refresh_token
        
        user.refresh_token_expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        
        session.add(user)
        await session.commit()
        
        return LoginResponseModel(
            message="Login Successful",
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserReadModel(
                id=str(user.id),
                email=user.email,
                username=user.username
            )
        )
    
    except Exception as e:
        await session.rollback()
        logging.error(f"Login error: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process login.",
            error_code=INTERNAL_SERVER_ERROR
        )

async def refresh_access_token_service(refresh_token: str, session: AsyncSession) -> RefreshTokenResponse:
    try:
        token_data = decode_token(refresh_token)
        if not token_data or not token_data.get('refresh'):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing token",
                error_code=AUTH_INVALID_TOKEN
            )
        
        user_id = token_data['user']['user_id']
        
        # Validate user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                error_code=AUTH_USER_NOT_FOUND_FOR_TOKEN
            )
            
        # Validate DB match
        if user.refresh_token != refresh_token:
            
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token mismatch",
                error_code=AUTH_TOKEN_MISMATCH
            )
            
        # Validate Expiry (DB check)
        if user.refresh_token_expires_at < datetime.now(timezone.utc):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
                error_code=AUTH_TOKEN_EXPIRED
            )
            
        # Create new Access Token
        
        new_access_token = create_access_token(
            user_data={
                'email': user.email,
                'user_id': str(user.id), 
            },
            expiry=timedelta(minutes=15)
        )
        
        logging.info(f"Access token refreshed for user: {user.id}")
        return RefreshTokenResponse(access_token=new_access_token)
        
    except AppException:
        raise
    except Exception as e:
        logging.error(f"Refresh error: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token",
            error_code=INTERNAL_SERVER_ERROR
        )

async def logout(user: User, session: AsyncSession) -> dict:
    try:
        user.refresh_token = None
        user.refresh_token_expires_at = None
        session.add(user)
        await session.commit()
        return {"message": "Logged out successfully"}
    except Exception as e:
        await session.rollback()
        logging.error(f"Logout error: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout",
            error_code=INTERNAL_SERVER_ERROR
        )