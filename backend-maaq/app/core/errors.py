from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "APP_ERROR",
        field: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        self.field = field
        self.details = details
        super().__init__(message)
