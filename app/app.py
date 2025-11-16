from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
#from app.database.schemas import UserCreate, UserRead, UserUpdate
#from app.users import fastapi_users

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.db import create_db_and_tables, get_async_session, Post, User, Comment, Upvote, SortBy
#from app.users import current_active_user

from app.routers.auth_router import router as auth_router
from app.routers.posts_router import router as posts_router
from app.routers.user_router import router as users_router

origins = [
    "http://localhost:5173",
    "http://localhost:3000", 
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(auth_router, tags=["auth"])

app.include_router(posts_router, tags=["posts"])

app.include_router(users_router, tags=["users"])



