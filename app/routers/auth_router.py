from app.database.schemas import UserCreateModel, LoginResponseModel, UserReadModel, UserLoginModel
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_async_session
from app.services.auth_services import register, login

router = APIRouter(tags=["auth"])

@router.post("/register", 
            response_model = UserReadModel,status_code=status.HTTP_201_CREATED)
async def register_route(
    register_data: UserCreateModel,
    session: AsyncSession = Depends(get_async_session)
):
    return await register(register_data=register_data, session=session)


@router.post("/login",
             response_model = LoginResponseModel,status_code=status.HTTP_200_OK)
async def login_route(
    login_data: UserLoginModel,
    session: AsyncSession = Depends(get_async_session)
):
    
    return await login(login_data=login_data, session=session)