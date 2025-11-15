import os, uuid, shutil, tempfile
from fastapi import HTTPException, UploadFile, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.db import Post, Upvote, Comment, User
from app.database.images import imagekit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from app.database.schemas import PostCreateModel, UpvoteCreateModel, UpvoteResponse, CommentCreateModel, UserReadModel, CommentResponse, PostResponseModel

from uuid import UUID
import logging

ALLOWED_FILE_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/quicktime"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


async def validate_file(file: UploadFile) -> None:
    """Validate file type and size"""
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {ALLOWED_FILE_TYPES}"
        )
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

async def upload_post(post_data: PostCreateModel, 
                      file: UploadFile,
                      user, 
                      session: AsyncSession ):
    
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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload file to storage"
            )
        
        file_type = "video" if file.content_type.startswith("video/") else "image"

        post = Post(
            user_id=user.id,
            caption=post_data.caption,
            url=upload_result.url,
            file_type=file_type,
            file_name=upload_result.name
        )
        
        session.add(post)
        await session.commit()
        await session.refresh(post)
        
        logging.info(f"Post created successfully: {post.id} by user {user.id}")
        return post
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error uploading post: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during upload"
        )
    finally:
        # Cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logging.warning(f"Failed to delete temp file: {e}")
        
        await file.close()

async def delete_post(post_id: str, 
                      user: User, 
                      session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")
    
    result = await session.execute(select(Post).where(Post.id == post_uuid))
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    if post.user_id != user.id and not  user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    
    try:
        await session.delete(post)
        await session.commit()
        return {"message": "Post deleted successfully"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete post")

async def upvote_post(post_id: str, 
                      user: User, 
                      session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    result = await session.execute(
        select(Post)
        .options(selectinload(Post.user))
        .where(Post.id == post_uuid)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    existing = await session.execute(
        select(Upvote).where(
            Upvote.post_id == post_uuid,
            Upvote.user_id == user.id
        )
    )
    
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already upvoted"
        )
    
    try:
        upvote = Upvote(post_id=post_uuid, user_id=user.id)
        session.add(upvote)
        await session.commit()
        
        logging.info(f"User {user.id} upvoted post {post_uuid}")
        return UpvoteResponse(message="Post upvoted successfully")
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upvote post"
        )

async def remove_upvote(
    post_id: str,
    user: User,
    session: AsyncSession
) -> UpvoteResponse:
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    upvote = await session.execute(
        select(Upvote).where(
            Upvote.post_id == post_uuid,
            Upvote.user_id == user.id
        )
    )
    upvote_record = upvote.scalar_one_or_none()
    
    if not upvote_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upvote not found"
        )
    
    try:
        await session.delete(upvote_record)
        await session.commit()
        
        logging.info(f"User {user.id} removed upvote from post {post_uuid}")
        return UpvoteResponse(message="Upvote removed successfully")
    except Exception as e:
        await session.rollback()
        logging.error(f"Error removing upvote: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove upvote"
        )


async def comment_on_post(post_id: str, 
                          comment_body: CommentCreateModel, 
                          user: User, 
                          session: AsyncSession):

    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post ID format"
        )
    
    post_result = await session.execute(
        select(Post).where(Post.id == post_uuid)
    )
    post = post_result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

async def get_post_detail(post_id: str, user, session: AsyncSession):
    try:
        post_uuid = UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid post ID format")
    

    result = await session.execute(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.comments).selectinload(Comment.user)
        )
        .where(Post.id == post_uuid)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    #
    upvote_result = await session.execute(
        select(Upvote).where(
            Upvote.user_id == user.id,
            Upvote.post_id == post.id
        )
    )
    is_upvoted = upvote_result.scalar_one_or_none() is not None
    
    #
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
        upvote_count=post.upvote_count,
        comment_count=post.comment_count,
        user_info=UserReadModel(
            email=post.user.email if post.user else "Unknown",
            username=post.user.username if post.user else "Unknown"
        ),
        comments=comments_list
    )

