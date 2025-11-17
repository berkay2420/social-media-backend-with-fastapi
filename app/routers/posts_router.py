from fastapi import APIRouter, UploadFile, File, Form, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database.db import get_async_session, User
from app.auth_dependencies import current_active_user, require_admin
from app.database.schemas import (
    DeletionResponse, 
    UpvoteResponse, 
    CommentResponse, 
    PostCreateModel, 
    PostResponseModel,
    TextPostResponse,
    TextPostCreateRequest,
    CommentCreateModel,
    AppErrorResponse,
    ValidationErrorResponse,
    UserReadModel
)
from app.services.posts_services import (
    upload_post,
    delete_post,
    upvote_post,
    remove_upvote,
    comment_on_post,
    get_post_detail,
    get_feed_service,
    upload_post_media,
    create_text_post
)
from app.exception_utils import AppException
from app.exception_utils import (
    POST_INVALID_ID_FORMAT,
    POST_NOT_FOUND,
    POST_INVALID_FILE_TYPE,
    POST_FILE_TOO_LARGE,
    POST_UPLOAD_FAILED,
    POST_ALREADY_UPVOTED,
    UPVOTE_NOT_FOUND,
    POST_INVALID_SORT_KEY,
    PERMISSION_DENIED,
    INTERNAL_SERVER_ERROR,
    INVALID_PAGINATION
)

router = APIRouter(prefix="/posts", tags=["posts"])

@router.post(
    "/upload",
    response_model=PostResponseModel,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid file type"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_413_CONTENT_TOO_LARGE: {
            "model": AppErrorResponse,
            "description": "File size too large"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ValidationErrorResponse,
            "description": "Validation error (e.g., empty caption)"
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": AppErrorResponse,
            "description": "Failed to upload file to storage"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Internal server error"
        }
    }
)
async def upload_file(
    file: UploadFile = File(...),
    caption: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upload a new image or video post with a caption."""
    post_data = PostCreateModel(caption=caption) 
    # Note: Service call signature was (post_data, file, user, session)
    # Swapping to match your original call
    return await upload_post(post_data, file, user, session)

@router.delete(
    "/{post_id}", 
    response_model=DeletionResponse, 
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid post ID format"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_403_FORBIDDEN: {
            "model": AppErrorResponse,
            "description": "Permission denied"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": AppErrorResponse,
            "description": "Post not found"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to delete post"
        }
    }
)
async def delete_post_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a post. Only the owner or an admin can delete."""
    return await delete_post(post_id, user, session)

@router.post(
    "/{post_id}/upvote",
    response_model=UpvoteResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid post ID format or post already upvoted"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": AppErrorResponse,
            "description": "Post not found"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to upvote post"
        }
    }
)
async def upvote_post_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upvote a post."""
    return await upvote_post(post_id, user, session)


@router.delete(
    "/{post_id}/upvote",
    response_model=UpvoteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid post ID format"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": AppErrorResponse,
            "description": "Upvote not found"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to remove upvote"
        }
    }
)
async def remove_upvote_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Remove an upvote from a post."""
    return await remove_upvote(post_id, user, session)


@router.post(
    "/{post_id}/comment", 
    response_model=CommentResponse, 
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid post ID format"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": AppErrorResponse,
            "description": "Post not found"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ValidationErrorResponse,
            "description": "Validation error (e.g., empty comment)"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to create comment"
        }
    }
)
async def comment_on_post_route(
    post_id: str,
    comment_body: CommentCreateModel,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Add a comment to a post."""
    return await comment_on_post(post_id, comment_body, user, session)

@router.get(
    "/{post_id}", 
    response_model=PostResponseModel, 
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid post ID format"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": AppErrorResponse,
            "description": "Post not found"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to process post details"
        }
    }
)
async def get_post_detail_route(
    post_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get detailed information about a single post."""
    return await get_post_detail(post_id, user, session)


@router.get(
    "", 
    response_model=list[PostResponseModel], 
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Invalid pagination or sort key"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to fetch feed"
        }
    }
)
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
    
@router.post(
    "/media/upload",
    response_model=PostResponseModel,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": AppErrorResponse},
        status.HTTP_401_UNAUTHORIZED: {"model": AppErrorResponse},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": AppErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": AppErrorResponse}
    }
)
async def upload_media_post(
    file: UploadFile = File(...),
    caption: str = Form(...),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Upload a media post (image or video)."""
    return await upload_post_media(caption, file, user, session)


@router.post(
    "/text",
    response_model=TextPostResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": AppErrorResponse,
            "description": "Missing title or content"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "model": AppErrorResponse,
            "description": "Authentication required"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ValidationErrorResponse,
            "description": "Validation error (title/content too long/short)"
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": AppErrorResponse,
            "description": "Failed to create text post"
        }
    }
)
async def create_text_post_route(
    request_body: TextPostCreateRequest,  
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Create a text post (Reddit-style, no media)."""
    post = await create_text_post(request_body.title, request_body.content, user, session)
    
    # Build response
    return TextPostResponse(
        id=str(post.id),
        user_id=str(post.user_id),
        post_type=post.post_type,
        title=post.title,
        content=post.caption,
        created_at=post.created_at.isoformat(),
        is_owner=post.user_id == user.id,
        upvote_count=post.upvote_count,
        comment_count=post.comment_count,
        is_upvoted_by_me=False,  # New posts can't be upvoted by creator yet
        user_info=UserReadModel(
            id=str(user.id),
            email=user.email,
            username=user.username
        ),
        comments=[]
    )