from pydantic import BaseModel, Field, field_validator, EmailStr, ConfigDict
from fastapi_users import schemas
import re
from typing import Any, Optional
from datetime import datetime


# USER SCHEMAS


class UserReadModel(BaseModel):
    id: str
    email: str
    username: str
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None
    
    model_config = ConfigDict(from_attributes=True)

class CurrentUserResponse(BaseModel):
    id: str
    email: str
    username: str
    total_upvotes: int
    posts_count: int  
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None
    
    model_config = ConfigDict(from_attributes=True)

class PasswordValidator:
    MIN_LENGTH = 10
    UPPERCASE = r'[A-Z]'
    LOWERCASE = r'[a-z]'
    DIGIT = r'\d'
    SPECIAL_CHARS = r'[@$!%*?&#]'
    
    RULES = [
        (MIN_LENGTH, f"Password must be at least {MIN_LENGTH} characters long"),
        (UPPERCASE, "Password must contain at least one uppercase letter"),
        (LOWERCASE, "Password must contain at least one lowercase letter"),
        (DIGIT, "Password must contain at least one digit"),
        (SPECIAL_CHARS, "Password must contain at least one special character (@$!%*?&#)")
    ]
    
    @classmethod
    def validate(cls, password: str) -> str:
        for rule, message in cls.RULES:
            if isinstance(rule, int):
                if len(password) < rule:
                    raise ValueError(message)
            else:
                if not re.search(rule, password):
                    raise ValueError(message)
        return password

class UserCreateModel(BaseModel):
    username: str = Field(max_length=10)
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return PasswordValidator.validate(v)

class UserLoginModel(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginResponseModel(BaseModel):
    message: str
    access_token: str
    refresh_token: str
    user: UserReadModel

class UserUpdate(schemas.BaseUserUpdate):
    pass

class UserUpdateModel(BaseModel):
    username: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=30)
    
    model_config = ConfigDict(from_attributes=True)

class UserDetailResponse(BaseModel):
    id: str
    email: str
    username: str
    total_upvotes: int
    posts_count: int
    created_at: str | None
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None
    
    model_config = ConfigDict(from_attributes=True)



# AUTH & TOKENS


class RefreshTokenRequest(BaseModel):
    refresh_token: str
    
class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"



# COMMENTS


class CommentCreateModel(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)

class CommentResponse(BaseModel):
    id: str
    user_id: str
    username: str
    user_email: str
    content: str
    created_at: str
    
    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v else None
    
    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v) if v else None
    
    model_config = ConfigDict(from_attributes=True)



# POSTS
class PostCreateModel(BaseModel):
    """Unified model for internal service creation logic"""
    post_type: str  # "MEDIA" or "TEXT"
    caption: str | None = None
    title: str | None = None

class PostCreateMediaModel(BaseModel):
    """Schema specifically for Media creation endpoint"""
    caption: str = Field(..., min_length=1, max_length=2000)

class TextPostCreateRequest(BaseModel):
    """Schema for creating a text post via API"""
    title: str = Field(..., min_length=1, max_length=300, description="Post title")
    content: str = Field(..., min_length=1, max_length=5000, description="Post content/body")
    
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "title": "My thoughts on FastAPI",
                "content": "This framework is amazing because it's fast..."
            }
        }
    )

class PostResponseModel(BaseModel):
    """
    Main response model for Feeds and Media Posts.
    Updated to handle both Media (has url) and Text (no url) posts.
    """
    id: str
    user_id: str
    caption: str
    
    # Made Optional for Text Posts in the Feed
    url: str | None = None
    file_type: str | None = None
    
    # Added Optional Title for Text Posts in the Feed
    title: str | None = None
    
    created_at: str
    is_owner: bool
    is_upvoted_by_me: bool
    upvote_count: int
    comment_count: int
    user_info: UserReadModel
    comments: list[CommentResponse]
    
    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None

    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v) if v else None

    model_config = ConfigDict(from_attributes=True)

class TextPostResponse(BaseModel):
    """Response specifically for Text Post creation"""
    id: str
    user_id: str
    post_type: str
    title: str
    content: str 
    
    created_at: str
    is_owner: bool
    upvote_count: int
    comment_count: int
    is_upvoted_by_me: bool
    user_info: UserReadModel
    comments: list[CommentResponse]
    
    @field_validator('id', 'user_id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None
    
    @field_validator('created_at', mode='before')
    @classmethod
    def convert_datetime_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v) if v else None
    
    model_config = ConfigDict(from_attributes=True)



# UPVOTES

class UpvoteCreateModel(BaseModel):
    pass

class UpvoteResponse(BaseModel):
    message: str
    
class UpvoteDetailResponse(BaseModel):
    id: str
    user_id: str
    post_id: str
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)

class DeletionResponse(BaseModel):
    message: str



# ERRORS


class ErrorResponse(BaseModel):
    """Standard error response structure"""
    detail: str
    error_code: str 
    timestamp: str 
    path: Optional[str] = None

class AppErrorResponse(BaseModel):
    """Wrapper for documentation purposes"""
    detail: str
    error_code: str
    timestamp: str  
    path: str
    
    model_config = ConfigDict(from_attributes=True)

class ValidationErrorResponse(ErrorResponse):
    """Validation errors"""
    errors: list[dict[str, Any]]