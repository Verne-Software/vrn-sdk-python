from __future__ import annotations

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._delayed import AsyncDelayedResource, DelayedResource
from ._jobs import AsyncJobsResource, JobsResource

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0


class Clockwork:
    """Synchronous client for the Verne Clockwork service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._http = SyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._jobs: JobsResource | None = None
        self._delayed: DelayedResource | None = None

    @property
    def jobs(self) -> JobsResource:
        if self._jobs is None:
            self._jobs = JobsResource(self._http)
        return self._jobs

    @property
    def delayed(self) -> DelayedResource:
        if self._delayed is None:
            self._delayed = DelayedResource(self._http)
        return self._delayed


class AsyncClockwork:
    """Asynchronous client for the Verne Clockwork service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._http = AsyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._jobs: AsyncJobsResource | None = None
        self._delayed: AsyncDelayedResource | None = None

    @property
    def jobs(self) -> AsyncJobsResource:
        if self._jobs is None:
            self._jobs = AsyncJobsResource(self._http)
        return self._jobs

    @property
    def delayed(self) -> AsyncDelayedResource:
        if self._delayed is None:
            self._delayed = AsyncDelayedResource(self._http)
        return self._delayed
