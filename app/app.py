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



#app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])

# @app.get("/feed")
# async def get_feed(
#     session: AsyncSession = Depends(get_async_session),
#     user: User = Depends(current_active_user),
#     sort_by: SortBy = Query(SortBy.NEW, description="Sorting Criteria: 'new', 'top', 'most_commented'"),
#     skip: int = 0, 
#     limit: int = 10 
# ):
    
#     sort_mapping = {
#         SortBy.NEW: Post.created_at.desc(),
#         SortBy.TOP: Post.upvote_count.desc(), # 'column_property' 
#         SortBy.MOST_COMMENTED: Post.comment_count.desc() # 'column_property' 
#     }
    
#     order_clause = sort_mapping[sort_by]
    
#     # Fetch all posts from the database, and also collect their user IDs
#     # to fetch all related users in a single follow-up query.
#     # This is the more efficient way.
#     # The alternative would be to fetch all posts first,
#     # and then for each post, make a separate query to get its user.
#     # Example: 10 posts → 10 extra queries (total ~11) vs just 2 queries (10 + 1).
#     query = (
#         select(Post)
#         .options(
#             selectinload(Post.user), 
#         )
#         .order_by(order_clause) #sort type
#         .offset(skip)
#         .limit(limit)
#     )
    
#     result = await session.execute(query)
#     posts = result.scalars().unique().all()

    
#     post_ids = [post.id for post in posts]
#     user_upvoted_set = set() 

#     if post_ids: 
#         upvoted_result = await session.execute(
#             select(Upvote.post_id)
#             .where(Upvote.user_id == user.id)
#             .where(Upvote.post_id.in_(post_ids))
#         )
        
#         user_upvoted_set = {pid for pid in upvoted_result.scalars().all()}

    
#     posts_data = []
#     for post in posts:
#         posts_data.append(
#             {
#                 "id": str(post.id),
#                 "user_id": str(post.user_id),
#                 "caption": post.caption,
#                 "url": post.url,
#                 "file_type": post.file_type,
#                 "created_at": post.created_at.isoformat(),
                
               
#                 "is_owner": post.user_id == user.id,
#                 "is_upvoted_by_me": post.id in user_upvoted_set, 
                
                
#                 "upvote_count": post.upvote_count,
#                 "comment_count": post.comment_count,
                
                
#                 "user_info": {
#                     "email": post.user.email if post.user else "Unknown",
#                     "username": post.user.username if post.user else "Unknown"
#                 },
                
#                 "comments": [] 
#             }
#         )

#     return {"posts": posts_data}


