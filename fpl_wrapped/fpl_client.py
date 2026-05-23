import asyncio
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from .config import Settings


class FPLClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client
        self.semaphore = asyncio.Semaphore(Settings.CONCURRENCY_LIMIT)

    async def _get_json(self, path: str, timeout: float = Settings.DEFAULT_LIVE_TIMEOUT) -> Dict[str, Any]:
        url = f"{Settings.FPL_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        async with self.semaphore:
            try:
                response = await self.client.get(url, timeout=timeout)
            except httpx.RequestError as exc:
                raise HTTPException(status_code=503, detail="Unable to reach FPL endpoint.") from exc

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="FPL resource not found.")
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="FPL rate limit reached.")
            response.raise_for_status()
            return response.json()

    async def get_bootstrap(self) -> Dict[str, Any]:
        return await self._get_json("bootstrap-static/")

    async def get_history(self, manager_id: int) -> Dict[str, Any]:
        return await self._get_json(f"entry/{manager_id}/history/")

    async def get_event_live(self, event_id: int) -> Dict[str, Any]:
        return await self._get_json(f"event/{event_id}/live/")

    async def get_picks(self, manager_id: int, event_id: int) -> Dict[str, Any]:
        return await self._get_json(f"entry/{manager_id}/event/{event_id}/picks/")
