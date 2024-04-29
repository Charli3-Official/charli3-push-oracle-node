"""Base model for all models."""

from datetime import datetime
from uuid import UUID
from sqlmodel import SQLModel as _SQLModel, Field
from sqlalchemy.orm import declared_attr
from backend.utils.uuid6 import uuid7


class SQLModel(_SQLModel):
    """Base model for all models."""

    @declared_attr
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()


class BaseUUIDModel(SQLModel):
    """Base model for all models with UUID primary key and timestamps."""

    id: UUID = Field(
        default_factory=uuid7,
        primary_key=True,
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Always has a value
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
