"""
Standardized error responses for the API.
"""
from enum import Enum
from typing import Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    # Client errors (4xx)
    NOT_FOUND = "RESOURCE_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"

    # Business logic errors
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    PIPELINE_ERROR = "PIPELINE_ERROR"


class ErrorDetail(BaseModel):
    """Standardized error detail structure."""
    code: str
    message: str
    resource: Optional[str] = None
    resource_id: Optional[Any] = None
    field: Optional[str] = None
    details: Optional[dict] = None


class APIError(HTTPException):
    """Custom API exception with standardized error format."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        resource: Optional[str] = None,
        resource_id: Optional[Any] = None,
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        detail = ErrorDetail(
            code=code.value,
            message=message,
            resource=resource,
            resource_id=resource_id,
            field=field,
            details=details,
        ).model_dump(exclude_none=True)

        super().__init__(status_code=status_code, detail=detail)


# Convenience functions for common errors

def not_found(resource: str, resource_id: Any = None, message: Optional[str] = None) -> APIError:
    """Create a 404 Not Found error."""
    return APIError(
        status_code=404,
        code=ErrorCode.NOT_FOUND,
        message=message or f"{resource} not found",
        resource=resource,
        resource_id=resource_id,
    )


def bad_request(message: str, field: Optional[str] = None, details: Optional[dict] = None) -> APIError:
    """Create a 400 Bad Request error."""
    return APIError(
        status_code=400,
        code=ErrorCode.BAD_REQUEST,
        message=message,
        field=field,
        details=details,
    )


def validation_error(message: str, field: str, details: Optional[dict] = None) -> APIError:
    """Create a 422 Validation Error."""
    return APIError(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        field=field,
        details=details,
    )


def unauthorized(message: str = "Authentication required") -> APIError:
    """Create a 401 Unauthorized error."""
    return APIError(
        status_code=401,
        code=ErrorCode.UNAUTHORIZED,
        message=message,
    )


def forbidden(message: str = "Permission denied") -> APIError:
    """Create a 403 Forbidden error."""
    return APIError(
        status_code=403,
        code=ErrorCode.FORBIDDEN,
        message=message,
    )


def internal_error(message: str = "An unexpected error occurred", details: Optional[dict] = None) -> APIError:
    """Create a 500 Internal Server Error."""
    return APIError(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message=message,
        details=details,
    )


def conflict(resource: str, message: str, resource_id: Optional[Any] = None) -> APIError:
    """Create a 409 Conflict error."""
    return APIError(
        status_code=409,
        code=ErrorCode.CONFLICT,
        message=message,
        resource=resource,
        resource_id=resource_id,
    )


def quota_exceeded(message: str = "Quota exceeded", details: Optional[dict] = None) -> APIError:
    """Create a 429 Quota Exceeded error."""
    return APIError(
        status_code=429,
        code=ErrorCode.QUOTA_EXCEEDED,
        message=message,
        details=details,
    )


def rate_limited(message: str = "Rate limit exceeded", details: Optional[dict] = None) -> APIError:
    """Create a 429 Rate Limited error."""
    return APIError(
        status_code=429,
        code=ErrorCode.RATE_LIMITED,
        message=message,
        details=details,
    )


def pipeline_error(message: str, details: Optional[dict] = None) -> APIError:
    """Create a 500 Pipeline Error."""
    return APIError(
        status_code=500,
        code=ErrorCode.PIPELINE_ERROR,
        message=message,
        details=details,
    )
