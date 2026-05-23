from typing import Optional
from pydantic import BaseModel


class ChipAnalysis(BaseModel):
    played: bool
    gw: Optional[int]
    status: str
    text: str


class WrappedResponse(BaseModel):
    manager_id: int
    overall_rank: str
    peak_rank: str
    total_points: int
    bench_pain: int
    transfers_made: int
    hit_cost: int
    tc_data: ChipAnalysis
    bb_data: ChipAnalysis
    archetype: str
    description: str
    # Tactical persona derived from transfers and hits
    persona: str
    persona_description: str
    transfer_activity: float
    hit_aggression: float
    finish_category: str
    finish_desc: str
    extended_ready: bool = False
    season_captain_points: int = 0
    captain_curse_count: int = 0
    stellar_captain_count: int = 0
    total_players: int = 10_000_000
