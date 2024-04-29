"""Base CRUD class for all models."""

from typing import Any, Generic, TypeVar, List, Optional
from uuid import UUID
from sqlmodel import SQLModel, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=SQLModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=SQLModel)


class BaseCrud(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD class for all models."""

    def __init__(self, model: ModelType):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLModel model class
        """
        self.model = model

    async def get(self, *, id: UUID, db_session: AsyncSession) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)
        result = await db_session.execute(query)
        return result.scalars().first()

    async def get_by_ids(
        self, *, ids: List[UUID], db_session: AsyncSession
    ) -> List[ModelType]:
        """Get a list of records by IDs."""
        query = select(self.model).where(self.model.id.in_(ids))
        result = await db_session.execute(query)
        return result.scalars().all()

    async def get_count(self, db_session: AsyncSession) -> int:
        """Get a count of records."""
        query = select(func.count()).select_from(select(self.model).subquery()) #pylint: disable=no-member,E1102
        result = await db_session.execute(query)
        return result.scalar_one()

    async def get_multi(
        self, *, skip: int = 0, limit: int = 100, db_session: AsyncSession
    ) -> List[ModelType]:
        """Get multiple records with optional skip and limit."""
        query = select(self.model).offset(skip).limit(limit).order_by(self.model.id)
        result = await db_session.execute(query)
        return result.scalars().all()

    async def create(
        self, *, obj_in: CreateSchemaType, db_session: AsyncSession
    ) -> ModelType:
        """Create a new record."""
        db_obj = self.model.model_validate(obj_in)
        db_session.add(db_obj)
        try:
            await db_session.commit()
            await db_session.refresh(db_obj)
        except IntegrityError as e:
            await db_session.rollback()
            # Handle or re-raise exception
            raise e
        return db_obj

    async def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        db_session: AsyncSession
    ) -> ModelType:
        """Update a record."""
        obj_data = db_obj.model_dump()
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj

    async def remove(self, *, id: UUID, db_session: AsyncSession) -> ModelType:
        """Remove a record by ID."""
        obj = await self.get(id=id, db_session=db_session)
        if not obj:
            raise ValueError("Record not found")
        await db_session.delete(obj)
        await db_session.commit()
        return obj
