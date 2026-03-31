from __future__ import annotations


class VerneError(Exception):
    """Base exception for all Verne SDK errors (network, timeout, etc.)."""


class VerneAPIError(VerneError):
    """Raised when the API returns an error response."""

    def __init__(self, code: str, message: str, status: int, request_id: str) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.request_id = request_id

    def __repr__(self) -> str:
        return (
            f"VerneAPIError(code={self.code!r}, status={self.status}, "
            f"request_id={self.request_id!r}, message={str(self)!r})"
        )
