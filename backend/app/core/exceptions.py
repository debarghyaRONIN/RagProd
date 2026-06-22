from fastapi import HTTPException, status

class BaseAPIException(HTTPException):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred"
    code: str = "INTERNAL_SERVER_ERROR"

    def __init__(self, detail: str | None = None, headers: dict | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(
            status_code=self.status_code,
            detail={"detail": self.detail, "code": self.code},
            headers=headers
        )

class CredentialsException(BaseAPIException):
    status_code: int = status.HTTP_401_UNAUTHORIZED
    detail: str = "Could not validate credentials"
    code: str = "UNAUTHORIZED"

    def __init__(self, detail: str | None = None):
        super().__init__(
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class ForbiddenException(BaseAPIException):
    status_code: int = status.HTTP_403_FORBIDDEN
    detail: str = "You do not have permission to access this resource"
    code: str = "FORBIDDEN"

class NotFoundException(BaseAPIException):
    status_code: int = status.HTTP_404_NOT_FOUND
    detail: str = "Resource not found"
    code: str = "NOT_FOUND"

class BadRequestException(BaseAPIException):
    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Bad request"
    code: str = "BAD_REQUEST"

class RateLimitException(BaseAPIException):
    status_code: int = status.HTTP_429_TOO_MANY_REQUESTS
    detail: str = "Too many requests, please slow down"
    code: str = "RATE_LIMIT_EXCEEDED"
