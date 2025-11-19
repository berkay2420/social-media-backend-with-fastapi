from collections.abc import AsyncGenerator
import uuid
from fastapi import Depends
from sqlalchemy import Index
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, column_property
from sqlalchemy.sql import select, func
from datetime import datetime, timezone
from enum import Enum
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL= os.getenv("SUPABASE_CONNECTION_URL")

class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    #one to many, one user have more than one post
    #if we put foreign key in user instead of post this means now the one post has more than one users
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    
    username = Column(String(length=50), unique=True, nullable=False)
    total_upvotes = Column(Integer, default=0, nullable=False)
    
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    
    refresh_token = Column(String, nullable=True)
    refresh_token_expires_at = Column(DateTime(timezone=True), nullable=True)

class Upvote(Base):
    __tablename__ = "upvotes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    post = relationship("Post", back_populates="comments")
    user = relationship("User")

class PostTypeEnum(str, Enum):
    MEDIA = "MEDIA"  
    TEXT = "TEXT" 

class Post(Base):
    __tablename__ = "posts"
    
    #ındexing for faster query
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_post_type', 'post_type'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    
    post_type = Column(SQLAlchemyEnum(PostTypeEnum), nullable=False, default=PostTypeEnum.MEDIA)
    title = Column(String(300), nullable=True)
    
    caption = Column(Text)
    url = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="posts")
    
    upvote_count = column_property(
        select(func.count(Upvote.id))
        .where(Upvote.post_id == id)
        .correlate_except(Upvote) 
        .scalar_subquery()
    )
    
    comment_count = column_property(
        select(func.count(Comment.id))
        .where(Comment.post_id == id)
        .correlate_except(Comment)
        .scalar_subquery()
    )
    
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    upvotes = relationship("Upvote", cascade="all, delete-orphan")

class SortBy(str, Enum):
    NEW = "new"  
    TOP = "top"  
    MOST_COMMENTED = "most_commented" 

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session  

#dependency injecytion
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
    
async def test_connection():
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1)) 
        print("✅ Successfully connected to Supabase!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")