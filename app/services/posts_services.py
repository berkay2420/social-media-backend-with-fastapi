from datetime import datetime, timezone
import os, shutil, tempfile
import logging
from uuid import UUID
from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions


from app.database.db import Post, Upvote, Comment, User, PostTypeEnum
from app.database.images import imagekit
from app.database.schemas import (
    PostCreateModel, 
    UpvoteResponse, 
    CommentCreateModel, 
    UserReadModel, 
    CommentResponse, 
    PostResponseModel
)
from app.exception_utils import (
    AppException,
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

ALLOWED_FILE_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


async def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {ALLOWED_FILE_TYPES}",
            error_code=POST_INVALID_FILE_TYPE
        )
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise AppException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB",
            error_code=POST_FILE_TOO_LARGE
        )

async def _handle_file_upload(file: UploadFile):
    """
    Helper function to handle file validation, temp file creation, 
    and ImageKit uploading to avoid code duplication.
    """
    await validate_file(file)
    
    temp_file_path = None
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            await file.seek(0)
            shutil.copyfileobj(file.file, temp_file)
            
        with open(temp_file_path, "rb") as f:
            upload_result = imagekit.upload_file(
                file=f,
                file_name=file.filename,
                options=UploadFileRequestOptions(
                    use_unique_file_name=True,
                    tags=["backend-upload"]
                ),
            )
            
        if upload_result.response_metadata.http_status_code != 200:
            logging.error(f"ImageKit upload failed: {upload_result}")
            raise AppException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload file to storage",
                error_code=POST_UPLOAD_FAILED
            )
            
        return upload_result

    except AppException:
        raise
    except Exception as e:
        logging.error(f"Error during file upload process: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload",
            error_code=INTERNAL_SERVER_ERROR
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logging.warning(f"Failed to delete temp file: {e}")
        await file.close()


async def upload_post(post_data: PostCreateModel, 
                      file: UploadFile,
                      user, 
                      session: AsyncSession ):
    
    upload_result = await _handle_file_upload(file)
    
    
    try:
        file_type = "video" if file.content_type.startswith("video/") else "image"
        
        caption_text = post_data.caption if hasattr(post_data, 'caption') else ""
        post = Post(
            user_id=user.id,
            post_type=PostTypeEnum.MEDIA,
            caption=caption_text,
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name
        )
        
        session.add(post)
        await session.commit()
        await session.refresh(post)  # Refresh to get server-generated values like created_at
        await session.expire(post)  # Clear from session
        await session.refresh(post) 
        
        logging.info(f"Post created successfully: {post.id} by user {user.id}")
            
        return PostResponseModel(
            id=str(post.id),
            user_id=str(post.user_id),
            caption=post.caption,
            url=post.url,
            file_type=file_type,  
            created_at=post.created_at.isoformat() if post.created_at else datetime.now(timezone.utc).isoformat(),
            is_owner=True,
            is_upvoted_by_me=False,
            upvote_count=0,
            comment_count=0,
            user_info=UserReadModel(
                id=str(user.id),
                email=user.email,
                username=user.username
            ),
            comments=[]
        )

    except Exception as e:
        logging.error(f"Error saving post to DB: {str(e)}", exc_info=True)
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during save",
            error_code=INTERNAL_SERVER_ERROR
        )

async def upload_post_media(
    caption: str,
    file: UploadFile,
    user: User,
    session: AsyncSession
):
    
    upload_result = await _handle_file_upload(file)
    
    try:
        file_type = "video" if file.content_type.startswith("video/") else "image"

        post = Post(
            user_id=user.id,
            post_type=PostTypeEnum.MEDIA,
            caption=caption,
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name
        )
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        await session.expire(post)  # Clear the object from session
        await session.refresh(post)
        
        logging.info(f"Media post created: {post.id} by user {user.id}")
        
        created_at = post.created_at if post.created_at else datetime.now(timezone.utc)
        
        return PostResponseModel(
            id=str(post.id),
            user_id=str(post.user_id),
            caption=post.caption,
            url=post.url,
            file_type=file_type,  
            created_at=created_at.isoformat(),
            is_owner=True,
            is_upvoted_by_me=False,
            upvote_count=0,
            comment_count=0,
            user_info=UserReadModel(
                id=str(user.id),
                email=user.email,
                username=user.username
            ),
            comments=[]
        )
    except Exception as e:
        logging.error(f"Error saving media post: {str(e)}", exc_info=True)
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create media post",
            error_code=INTERNAL_SERVER_ERROR
        )

async def create_text_post(
    title: str,
    content: str,
    user: User,
    session: AsyncSession
):
    
    try:
        post = Post(
            user_id=user.id,
            post_type=PostTypeEnum.TEXT,
            title=title,
            caption=content  # Store content in caption field
        )
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        logging.info(f"Text post created: {post.id} by user {user.id}")
        return post
        
    except Exception as e:
        logging.error(f"Error creating text post: {str(e)}", exc_info=True)
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create text post",
            error_code=INTERNAL_SERVER_ERROR
        )

async def delete_post(post_id: str, 
                      user: User, 
                      session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid post ID format",
            error_code=POST_INVALID_ID_FORMAT
        )
    
    result = await session.execute(select(Post).where(Post.id == post_uuid))
    post = result.scalar_one_or_none()
    
    if not post:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found",
            error_code=POST_NOT_FOUND
        )
    
    if post.user_id != user.id and not user.is_superuser:
        raise AppException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied",
            error_code=PERMISSION_DENIED
        )
    
    try:
        await session.delete(post)
        await session.commit()
        return {"message": "Post deleted successfully"}
    except Exception as e:
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to delete post",
            error_code=INTERNAL_SERVER_ERROR
        )

async def upvote_post(post_id: str, 
                      user: User, 
                      session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format",
            error_code=POST_INVALID_ID_FORMAT
        )
    
    result = await session.execute(
        select(Post).where(Post.id == post_uuid)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
            error_code=POST_NOT_FOUND
        )
    
    existing = await session.execute(
        select(Upvote).where(
            Upvote.post_id == post_uuid,
            Upvote.user_id == user.id
        )
    )
    
    if existing.scalar_one_or_none():
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already upvoted",
            error_code=POST_ALREADY_UPVOTED
        )
    
    try:
        upvote = Upvote(post_id=post_uuid, user_id=user.id)
        session.add(upvote)
        await session.commit()
        
        logging.info(f"User {user.id} upvoted post {post_uuid}")
        return UpvoteResponse(message="Post upvoted successfully")
    except Exception as e:
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upvote post",
            error_code=INTERNAL_SERVER_ERROR
        )

async def remove_upvote(
    post_id: str,
    user: User,
    session: AsyncSession
) -> UpvoteResponse:
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format",
            error_code=POST_INVALID_ID_FORMAT
        )
    
    upvote = await session.execute(
        select(Upvote).where(
            Upvote.post_id == post_uuid,
            Upvote.user_id == user.id
        )
    )
    upvote_record = upvote.scalar_one_or_none()
    
    if not upvote_record:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upvote not found",
            error_code=UPVOTE_NOT_FOUND
        )
    
    try:
        await session.delete(upvote_record)
        await session.commit()
        
        logging.info(f"User {user.id} removed upvote from post {post_uuid}")
        return UpvoteResponse(message="Upvote removed successfully")
    except Exception as e:
        await session.rollback()
        logging.error(f"Error removing upvote: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove upvote",
            error_code=INTERNAL_SERVER_ERROR
        )


async def comment_on_post(post_id: str, 
                          comment_body: CommentCreateModel, 
                          user: User, 
                          session: AsyncSession):

    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format",
            error_code=POST_INVALID_ID_FORMAT
        )
    
    post_result = await session.execute(
        select(Post).where(Post.id == post_uuid)
    )
    post = post_result.scalar_one_or_none()
    
    if not post:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
            error_code=POST_NOT_FOUND
        )
    
    try:
        comment = Comment(
            post_id=post_uuid,
            user_id=user.id,
            content=comment_body.content
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)
        
        return CommentResponse(
            id=str(comment.id),
            user_id=str(user.id),
            username=user.username,
            user_email=user.email,
            content=comment.content,
            created_at=comment.created_at.isoformat()
        )
    except Exception as e:
        await session.rollback()
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment",
            error_code=INTERNAL_SERVER_ERROR
        )

async def get_post_detail(post_id: str, user, session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid post ID format",
            error_code=POST_INVALID_ID_FORMAT
        )
    

    result = await session.execute(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.comments).selectinload(Comment.user),
            selectinload(Post.upvotes)
        )
        .where(Post.id == post_uuid)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found",
            error_code=POST_NOT_FOUND
        )
    
    try:
        upvote_result = await session.execute(
            select(Upvote).where(
                Upvote.user_id == user.id,
                Upvote.post_id == post.id
            )
        )
        is_upvoted = upvote_result.scalar_one_or_none() is not None
        
        comments_list = [
            CommentResponse(
                id=str(comment.id),
                user_id=str(comment.user_id),
                user_email=comment.user.email if comment.user else "Unknown",
                username=comment.user.username if comment.user else "Unknown",
                content=comment.content,
                created_at=comment.created_at.isoformat()
            )
            for comment in sorted(post.comments, key=lambda c: c.created_at, reverse=True)
        ]
        
        return PostResponseModel(
            id=str(post.id),
            user_id=str(post.user_id),
            caption=post.caption,
            url=post.url,
            file_type=post.file_type,
            created_at=post.created_at.isoformat(),
            is_owner=post.user_id == user.id,
            is_upvoted_by_me=is_upvoted,
            upvote_count=len(post.upvotes), 
            comment_count=len(post.comments),
            user_info=UserReadModel(
                id=str(post.user.id),
                email=post.user.email if post.user else "Unknown",
                username=post.user.username if post.user else "Unknown"
            ),
            comments=comments_list
        )
    except Exception as e:
        logging.error(f"Error processing post detail: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process post details",
            error_code=INTERNAL_SERVER_ERROR
        )

async def get_feed_service(
    skip: int = 0,
    limit: int = 10,
    sort_by: str = "new",
    user: User = None,
    session: AsyncSession = None
) -> list[PostResponseModel]:
    
    if skip < 0 or limit < 1 or limit > 100:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination parameters",
            error_code=INVALID_PAGINATION
        )
    
    if sort_by not in ["new", "top"]:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_by must be 'new' or 'top'",
            error_code=POST_INVALID_SORT_KEY
        )
    
    try:
       
        # Only load the User (author) info.
        query = select(Post).options(
            selectinload(Post.user)
        )
        
        # Sort
        if sort_by == "new":
            query = query.order_by(Post.created_at.desc())
        else:
            
            query = query.order_by(Post.upvote_count.desc())
        
        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        posts = result.scalars().all()
        
        if not posts:
            return []
        
        # IDs
        post_ids = [post.id for post in posts]
        
        # upvotes (batch check for current user)
        if user:
            upvotes_result = await session.execute(
                select(Upvote.post_id).where(
                    Upvote.user_id == user.id,
                    Upvote.post_id.in_(post_ids)
                )
            )
            
            upvoted_post_ids = set(str(row[0]) for row in upvotes_result.all())
        else:
            upvoted_post_ids = set()
        
        # Response
        feed = []
        for post in posts:
            created_at = post.created_at if post.created_at else datetime.now(timezone.utc)
            
            post_response = PostResponseModel(
                id=str(post.id),
                user_id=str(post.user_id),
                caption=post.caption,
                url=post.url,
                file_type=post.file_type,
                created_at=created_at.isoformat(),
                is_owner=user.id == post.user_id if user else False,
                
                
                is_upvoted_by_me=str(post.id) in upvoted_post_ids,
                
                
                upvote_count=post.upvote_count,
                comment_count=post.comment_count,
                
                user_info=UserReadModel(
                    id=str(post.user.id),
                    email=post.user.email if post.user else "Unknown",
                    username=post.user.username if post.user else "Unknown"
                ),
                #Feed does not show comments
                comments=[]
            )
            feed.append(post_response)
        
        logging.info(f"Feed: {len(feed)} posts, sort_by={sort_by}, queries=2")
        return feed
        
    except Exception as e:
        logging.error(f"Error fetching feed: {str(e)}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch feed",
            error_code=INTERNAL_SERVER_ERROR
        )