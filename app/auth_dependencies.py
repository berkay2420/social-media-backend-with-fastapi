from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.database.db import get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import decode_token
from sqlalchemy import select
import jwt
import logging
from uuid import UUID

async def current_active_user(token: str = Depends(HTTPBearer()),
                              session: AsyncSession = Depends(get_async_session)):
    
    try:
        token_data = decode_token(token.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        
        try:
            user_id = token_data['user']['user_id']
            # Validate format
            UUID(user_id) 
        except (KeyError, ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload invalid"
            )

        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if not user.is_active:  
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
            
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Auth dependency error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def require_admin(user: User = Depends(current_active_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user