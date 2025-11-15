import secrets
from datetime import datetime, timedelta
from app.database.db import RefreshToken, async_session_maker
import uuid

async def create_refresh_token(user_id: uuid.UUID):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    async with async_session_maker() as session:
        refresh = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        session.add(refresh)
        await session.commit()
    return token


def create_transformed_url(original_url: str, width: int = 300, height: int = 300) -> str:
    
    if not original_url:
        return ""
    
    parts = original_url.split("/")
    base_url = "/".join(parts[:4])
    file_path = "/".join(parts[4:])
    
    transformation = f"tr:w-{width},h-{height},cm-pad_resize"
    
    return f"{base_url}/{transformation}/{file_path}"
