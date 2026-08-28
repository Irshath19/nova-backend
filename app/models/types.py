import json
from typing import Any

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy import Text, TypeDecorator


class VectorType(TypeDecorator):
    """
    Vector type that uses pgvector.sqlalchemy.Vector on PostgreSQL,
    and falls back to JSON-serialized Text on SQLite for offline testing.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 768, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PgVector(self.dim))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value: list[float] | None, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return None
        if isinstance(value, (list, tuple)):
            return list(value)
        return value
