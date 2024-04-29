""" Jobs CRUD operations."""

from .base_crud import BaseCrud
from ..models.jobs import Job, JobCreate, JobUpdate


class JobsCrud(BaseCrud[Job, JobCreate, JobUpdate]):
    """Jobs CRUD operations."""

    pass  # pylint: disable=unnecessary-pass


jobs_crud = JobsCrud(Job)
