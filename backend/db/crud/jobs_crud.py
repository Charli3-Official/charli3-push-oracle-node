""" Jobs CRUD operations."""

from ..models.jobs import Job, JobCreate, JobUpdate
from .base_crud import BaseCrud


class JobsCrud(BaseCrud[Job, JobCreate, JobUpdate]):
    """Jobs CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


jobs_crud = JobsCrud(Job)
