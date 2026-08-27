from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    meta: dict | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
    total_pages: int
