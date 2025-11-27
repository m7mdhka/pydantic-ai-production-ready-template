"""Extra schemas for the application."""

from pydantic import BaseModel, Field


class HealthCheck(BaseModel):
    """Health check schema."""

    version: str = Field(..., description="The version of the application")
    status: str = Field(..., description="The status of the application")
