from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import User
import uuid
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.database.schemas import UserCreateModel, UserLoginModel, UserReadModel, RefreshTokenRequest
from app.utils import verify_password, create_access_token, generate_hash
from app.utils import create_access_token
from datetime import timedelta , datetime, timezone
from app.utils import decode_token
import logging

import jwt

REFRESH_TOKEN_EXPIRY = 2

async def register(register_data: UserCreateModel,
                   session: AsyncSession):
    
    username = register_data.username
    email = register_data.email
    password = register_data.password
    
    hashed_pw = generate_hash(password)
    
    new_user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_pw,
        username=username,
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
        logging.exception(e)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address or username already exists"
        )
        
    except SQLAlchemyError as e:
        await session.rollback()
        logging.exception(e) 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during user creation."
        )
    
    except Exception as e:
        await session.rollback()
        logging.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )
        
    

async def login(login_data: UserLoginModel, session: AsyncSession):
    email = login_data.email
    password = login_data.password
    
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(
        user_data={'email': user.email, 'user_id': str(user.id)}
    )
    refresh_token = create_access_token(
        user_data={'email': user.email, 'user_id': str(user.id)},
        refresh=True,
        expiry=timedelta(days=REFRESH_TOKEN_EXPIRY)
    )

    user.refresh_token = refresh_token
    user.refresh_token_expires_at = datetime.now() + timedelta(days=7)
    session.add(user)
    
    await session.commit()
    
    
    return {
        "message": "Login Successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserReadModel(
            id=str(user.id),
            email=user.email,
            username=user.username
        )
    }
    
    
async def refresh_access_token_service(refresh_token: str,
                               session: AsyncSession):
    try:
        token_data = decode_token(refresh_token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = token_data['user']['user_id']
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        if user.refresh_token != refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token mismatch"
            )
        if user.refresh_token_expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
            
        new_access_token = create_access_token(
            user_data={
                'email': user.email,
                'user_uuid': str(user.id),
            },
            expiry=timedelta(minutes=15)
        )
        
        logging.info(f"Access token refreshed for user: {user.id}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except Exception as e:
        logging.error(f"Error refreshing token: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )