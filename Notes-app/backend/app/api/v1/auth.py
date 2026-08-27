from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RefreshTokenRequest, TokenResponse, UserLogin, UserOut, UserRegister
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=ApiResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.register(payload)
    return ApiResponse(data=token_response)


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.login(payload)
    return ApiResponse(data=token_response)


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    token_response = await auth_service.refresh_token(payload.refresh_token)
    return ApiResponse(data=token_response)


@router.get("/me", response_model=ApiResponse[UserOut])
async def get_me(current_user: User = Depends(get_current_user)):
    return ApiResponse(data=UserOut.model_validate(current_user))


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(current_user: User = Depends(get_current_user)):
    return ApiResponse(data={"message": "Logged out successfully"})
