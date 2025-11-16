from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.database.db import get_async_session, User
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils import decode_token
from sqlalchemy import select
import jwt
import logging

async def current_active_user(token: str = Depends(HTTPBearer()),
                           session: AsyncSession = Depends(get_async_session)):
    
    try:
        token_data = decode_token(token.credentials)
        
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
        
        if not user.is_active:  
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
            
        return user
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException:
        raise
    except jwt.InvalidTokenError:  
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logging.error(f"Auth error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

async def require_admin(user: User = Depends(current_active_user)):
    if user.is_superuser != True:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user