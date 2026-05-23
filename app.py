import logging
from pathlib import Path
from typing import Any, Dict, List

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fpl_wrapped.cache import TTLCache
from fpl_wrapped.config import Settings
from fpl_wrapped.fpl_client import FPLClient
from fpl_wrapped.logic import build_bb_analysis, create_wrapped_payload
from fpl_wrapped.schemas import WrappedResponse

logger = logging.getLogger("fpl_wrapped")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

static_dir = Path(__file__).resolve().parent / "static"

app = FastAPI(title=Settings.APP_TITLE)

if Settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Settings.ALLOWED_ORIGINS,
        allow_methods=["GET"],
        allow_headers=["*"],
        allow_credentials=True,
    )

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "interest-cohort=()")
    return response


@app.on_event("startup")
async def startup_event():
    app.state.http_client = httpx.AsyncClient()
    app.state.fpl_client = FPLClient(app.state.http_client)
    app.state.cache = TTLCache(Settings.CACHE_TTL_SECONDS, Settings.CACHE_MAX_ENTRIES)
    app.state.player_registry: Dict[int, str] = {}
    app.state.global_event_cache: Dict[int, Dict[str, Any]] = {}
    app.state.total_players = 10_000_000

    try:
        bootstrap = await app.state.fpl_client.get_bootstrap()
        app.state.player_registry = {
            player["id"]: player["web_name"] for player in bootstrap.get("elements", [])
        }
        app.state.total_players = bootstrap.get("total_players", app.state.total_players)
        app.state.global_event_cache = {
            event["id"]: {
                "average": event.get("average_entry_score", 0),
                "highest": event.get("highest_score", 0),
            }
            for event in bootstrap.get("events", [])
        }
        logger.info(
            "Preloaded %d player profiles, total players=%s, event benchmarks=%d",
            len(app.state.player_registry),
            f"{app.state.total_players:,}",
            len(app.state.global_event_cache),
        )
    except Exception as exc:
        logger.warning("Failed to preload FPL bootstrap data: %s", exc)


@app.on_event("shutdown")
async def shutdown_event():
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()


@app.get("/api/wrapped/{manager_id}", response_model=WrappedResponse)
async def get_fpl_wrapped(manager_id: int, background_tasks: BackgroundTasks):
    if manager_id <= 0:
        raise HTTPException(status_code=400, detail="Manager ID must be a positive integer.")

    cached_payload = await app.state.cache.get(manager_id)
    if cached_payload:
        if not cached_payload.get("extended_ready"):
            background_tasks.add_task(
                hydrate_deep_captaincy_stats,
                manager_id,
                cached_payload.get("_current_season_gw_data", []),
            )
        return cached_payload

    fpl_data = await app.state.fpl_client.get_history(manager_id)
    current_season_gw_data = fpl_data.get("current", []) or []
    chips_played = fpl_data.get("chips", []) or []

    if not current_season_gw_data:
        raise HTTPException(status_code=400, detail="No active history rows found.")

    payload = create_wrapped_payload(
        manager_id=manager_id,
        current_season_gw_data=current_season_gw_data,
        chips_played=chips_played,
        global_event_cache=app.state.global_event_cache,
        total_players=app.state.total_players,
    )

    payload["bb_data"] = (await build_bb_analysis(manager_id, chips_played, app.state.fpl_client)).dict()
    payload["_current_season_gw_data"] = current_season_gw_data

    await app.state.cache.set(manager_id, payload)
    background_tasks.add_task(hydrate_deep_captaincy_stats, manager_id, current_season_gw_data)
    return payload


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", response_class=FileResponse)
async def serve_frontend():
    return static_dir / "index.html"


async def hydrate_deep_captaincy_stats(manager_id: int, current_season_gw_data: List[Dict[str, Any]]):
    if not current_season_gw_data:
        return

    season_captain_points = 0
    curse_incidents = 0
    stellar_incidents = 0

    for gw_entry in current_season_gw_data:
        gw = gw_entry.get("event")
        if not gw:
            continue

        live_cache_key = f"live_scores:{gw}"
        live_scores = await app.state.cache.get(live_cache_key)

        if live_scores is None:
            try:
                live_data = await app.state.fpl_client.get_event_live(gw)
                live_scores = {
                    element["id"]: element.get("stats", {}).get("total_points", 0)
                    for element in live_data.get("elements", [])
                }
                await app.state.cache.set(live_cache_key, live_scores)
            except Exception:
                continue

        try:
            picks_data = await app.state.fpl_client.get_picks(manager_id, gw)
            picks = picks_data.get("picks", [])
            captain = next((pick for pick in picks if pick.get("is_captain")), None)

            if captain:
                cap_id = captain.get("element")
                multiplier = captain.get("multiplier", 1)
                captain_points = live_scores.get(cap_id, 0) * multiplier
                season_captain_points += captain_points

                if captain_points <= 5:
                    curse_incidents += 1
                if captain_points >= 15:
                    stellar_incidents += 1
        
        except Exception:
            continue

    cached_payload = await app.state.cache.get(manager_id)
    if not cached_payload:
        return

    cached_payload["season_captain_points"] = season_captain_points
    cached_payload["captain_curse_count"] = curse_incidents
    cached_payload["stellar_captain_count"] = stellar_incidents
    cached_payload["extended_ready"] = True
    await app.state.cache.set(manager_id, cached_payload)
