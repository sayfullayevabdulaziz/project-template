from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status: int = 500
    title: str = "Internal Server Error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.headers: dict[str, str] = {}


class NotFound(DomainError):
    status = 404
    title = "Not Found"


class Conflict(DomainError):
    status = 409
    title = "Conflict"


class Unauthorized(DomainError):
    status = 401
    title = "Unauthorized"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.headers["WWW-Authenticate"] = "Bearer"


class Forbidden(DomainError):
    status = 403
    title = "Forbidden"


class RateLimited(DomainError):
    status = 429
    title = "Too Many Requests"

    def __init__(self, detail: str, retry_after: int) -> None:
        super().__init__(detail)
        self.headers["Retry-After"] = str(retry_after)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            {"type": "about:blank", "title": exc.title, "status": exc.status, "detail": exc.detail},
            status_code=exc.status,
            headers=exc.headers,
            media_type="application/problem+json",
        )
