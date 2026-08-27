from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister

security_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, payload: UserRegister) -> TokenResponse:
        existing_email = await self.user_repo.get_by_email(payload.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists",
            )

        existing_username = await self.user_repo.get_by_username(payload.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists",
            )

        hashed = hash_password(payload.password)
        user = await self.user_repo.create(
            email=payload.email,
            username=payload.username,
            password_hash=hashed,
        )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )

    async def login(self, payload: UserLogin) -> TokenResponse:
        user = await self.user_repo.get_by_email(payload.email_or_username)
        if not user:
            user = await self.user_repo.get_by_username(payload.email_or_username)

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email/username or password",
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserOut.model_validate(user),
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        user = await self.user_repo.get_by_id(str(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user=UserOut.model_validate(user),
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
