from pydantic import BaseModel, Field, field_validator, EmailStr
from fastapi_users import schemas
import uuid
import re


class UserReadModel(BaseModel):
    id: str
    email: str
    username: str
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        return str(v) if v else None
    
    class Config:
        from_attributes = True

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
    
    class Config:
        from_attributes = True

class CommentCreateModel(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)

class CommentResponse(BaseModel):
    id: str
    user_id: str
    username: str
    user_email: str
    content: str
    created_at: str
    
    class Config:
        from_attributes = True

class PostCreateModel(BaseModel):
    caption: str

class PostResponseModel(BaseModel):
    id: str
    user_id: str
    caption: str
    url: str
    file_type: str
    created_at: str
    is_owner: bool
    is_upvoted_by_me: bool
    upvote_count: int
    comment_count: int
    user_info: UserReadModel
    comments: list[CommentResponse]
    
    class Config:
        from_attributes = True

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

class UpvoteCreateModel(BaseModel):
    """Request model for creating an upvote"""
    pass

class UpvoteResponse(BaseModel):
    """Response model for upvote operations"""
    message: str
    
class UpvoteDetailResponse(BaseModel):
    """Detailed upvote information response"""
    id: str
    user_id: str
    post_id: str
    created_at: str
    
    class Config:
        from_attributes = True

class UpvoteResponse(BaseModel):
    message: str
        
class DeletionResponse(BaseModel):
    message: str
    
class UserUpdateModel(BaseModel):
    """Schema for updating user information"""
    username: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=30)
    
    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    """Detailed user information response"""
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
    
    class Config:
        from_attributes = True

class RefreshTokenRequest(BaseModel):
    refresh_token: str