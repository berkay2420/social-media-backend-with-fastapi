from fastapi import APIRouter, UploadFile, File, Form, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database.db import get_async_session, User
from app.auth_dependencies import current_active_user, require_admin
from app.database.schemas import DeletionResponse, UpvoteResponse, CommentResponse, PostCreateModel, PostResponseModel, CommentCreateModel
from app.services.posts_services import (
    upload_post,
    delete_post,
    upvote_post,
    remove_upvote,
    comment_on_post,
    get_post_detail,
    get_feed_service
)

router = APIRouter(prefix="/posts")

@router.post("/upload",
             response_model = PostResponseModel,status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    post_data = PostCreateModel(caption=caption) 
    return await upload_post(file, post_data, user, session)

@router.delete("/{post_id}", response_model=DeletionResponse, status_code=status.HTTP_200_OK)
async def delete_post_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await delete_post(post_id, user, session)

@router.post(
    "/{post_id}/upvote",
    response_model=UpvoteResponse,
    status_code=status.HTTP_201_CREATED
)
async def upvote_post_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await upvote_post(post_id, user, session)


@router.delete(
    "/{post_id}/upvote",
    response_model=UpvoteResponse,
    status_code=status.HTTP_200_OK
)
async def remove_upvote_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await remove_upvote(post_id, user, session)


@router.post("/{post_id}/comment", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def comment_on_post_route(
    post_id: str,
    comment_body: CommentCreateModel,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await comment_on_post(post_id, comment_body, user, session)

@router.get("/{post_id}", response_model=PostResponseModel, status_code=status.HTTP_200_OK)
async def get_post_detail_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    return await get_post_detail(post_id, user, session)


@router.get("", response_model=list[PostResponseModel], status_code=status.HTTP_200_OK)
async def get_feed_route(
    skip: int = Query(0, ge=0, description="Number of posts to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of posts to return"),
    sort_by: str = Query("new", description="Sort by: 'new' (latest) or 'top' (most upvoted)"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get paginated feed of all posts
    
    - **skip**: Offset for pagination (default: 0)
    - **limit**: Number of posts per page (default: 10, max: 100)
    - **sort_by**: "new" for latest posts, "top" for most upvoted
    """
    return await get_feed_service(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        user=user,
        session=session
    )