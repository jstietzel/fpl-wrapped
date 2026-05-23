from typing import Any, Dict, Iterable, List, Optional, Tuple

from .schemas import ChipAnalysis


def parse_rank_value(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return None


def format_rank(value: Any) -> str:
    parsed = parse_rank_value(value)
    return f"#{parsed:,}" if parsed is not None else str(value or "N/A")


def _find_chip_event(chips: Iterable[Dict[str, Any]], chip_name: str) -> Optional[int]:
    for chip in chips:
        if chip.get("name") == chip_name:
            return chip.get("event")
    return None


def build_tc_analysis(
    chips_played: List[Dict[str, Any]],
    current_season_gw_data: List[Dict[str, Any]],
    global_event_cache: Dict[int, Dict[str, Any]],
    total_players: int,
) -> ChipAnalysis:
    tc_gw = _find_chip_event(chips_played, "3xc")
    if not tc_gw:
        return ChipAnalysis(played=False, gw=None, status="neutral", text="Not deployed yet ⏳")

    gw_data = next((gw for gw in current_season_gw_data if gw.get("event") == tc_gw), None)
    points = gw_data.get("points", 0) if gw_data else 0
    rank = parse_rank_value(gw_data.get("rank") if gw_data else None) or 0
    avg = global_event_cache.get(tc_gw, {}).get("average", 50)

    if points < avg:
        status = "roast"
        text = f"Ouch! You hit {points} points in GW {tc_gw}, missing the global average of {avg}. Absolute disasterclass! 💀"
    elif rank and rank <= max(1, int(total_players * 0.25)):
        status = "worked"
        text = f"Masterclass! Your {points} points in GW {tc_gw} put you in the top 25% globally. The triple armband paid off beautifully! 🚀"
    else:
        status = "neutral"
        text = f"Decent. You locked in {points} points in GW {tc_gw} compared to the global average of {avg}. Respectable and secure."

    return ChipAnalysis(played=True, gw=tc_gw, status=status, text=text)


def build_archetype_analysis(total_transfers: int) -> Tuple[str, str]:
    if total_transfers > 55:
        description = f"You engineered {total_transfers} transfers. Your strategy was volatile, emotional, and highly erratic."
        archetype = "The Chaos Merchant 🌀"
    elif total_transfers < 30:
        description = f"Only {total_transfers} total transfers. You backed your initial squad layout implicitly, refusing to panic during tough runs."
        archetype = "The Diamond Hands 💎"
    else:
        description = f"With {total_transfers} moves completed, you struck a perfect structural equilibrium between active changes and patient holds."
        archetype = "The Balanced Tactician ⚖️"
    return archetype, description


def build_persona_quadrant(transfers_made: int, hit_cost: int) -> Tuple[str, str, float, float]:
    """
    Build a two-axis persona from transfers and hit cost using a quadrant approach.

    Returns (persona_label, description, transfer_activity, hit_aggression)
    - transfer_activity: normalized [0,1] based on a reasonable seasonal cap
    - hit_aggression: normalized [0,1] based on absolute hit cost seasonal cap
    """
    # Reasonable caps for normalization (seasonal expectations)
    TRANSFER_CAP = 60.0
    HIT_CAP = 20.0

    transfer_activity = max(0.0, min(1.0, transfers_made / TRANSFER_CAP))
    hit_aggression = max(0.0, min(1.0, abs(hit_cost) / HIT_CAP))

    is_high_transfers = transfers_made > 40
    is_high_hits = abs(hit_cost) >= 16

    if not is_high_transfers and not is_high_hits:
        persona = "Steady Captain"
        desc = f"Low transfer activity ({transfers_made}) and conservative hit usage ({hit_cost} pts). You prefer stability and trust your starting XI."
    elif is_high_transfers and not is_high_hits:
        persona = "Day Trader"
        desc = f"High transfer activity ({transfers_made}) but low hit cost ({hit_cost} pts). You pivot often without overpaying for moves."
    elif not is_high_transfers and is_high_hits:
        persona = "Big Spender"
        desc = f"Low transfer volume ({transfers_made}) yet high hit usage ({hit_cost} pts). You prefer fewer, costly gambles to force short-term advantage."
    else:
        persona = "Chaotic Gambler"
        desc = f"High transfer activity ({transfers_made}) and frequent/expensive hits ({hit_cost} pts). You chase volatility and big swings."

    return persona, desc, transfer_activity, hit_aggression


def build_finish_analysis(overall_rank: Any, peak_rank: Any) -> Tuple[str, str]:
    overall = parse_rank_value(overall_rank)
    peak = parse_rank_value(peak_rank)
    if overall is None or peak is None or peak <= 0:
        return (
            "Steady Contender 🏃",
            "Your campaign showed strong persistence throughout the season. Review your final stats breakdown below.",
        )

    if overall == peak:
        return (
            "Finished Strong 🏆",
            f"Absolute perfection! You ended the campaign at your absolute highest rank of the season ({format_rank(overall)}). Pure champion behavior!",
        )
    if overall <= 10000:
        return (
            "Finished Strong 💪",
            f"Elite finish! You ended at {format_rank(overall)}. Competing at this level is pure champion behavior.",
        )

    drop = overall - peak
    relative_drop = drop / peak

    strong_absolute_threshold = min(max(10000, int(peak * 0.03)), 50000)
    steady_absolute_threshold = min(max(50000, int(peak * 0.15)), 400000)

    if drop <= strong_absolute_threshold and relative_drop <= 0.05:
        return (
            "Finished Strong 💪",
            f"Excellent finish! You ended at {format_rank(overall)}, holding very close to your season peak of {format_rank(peak)}.",
        )
    if drop <= steady_absolute_threshold and relative_drop <= 0.40:
        return (
            "Stayed Steady ⚖️",
            f"A reliable campaign. You ended at {format_rank(overall)}, staying reasonably close to your peak of {format_rank(peak)}.",
        )
    return (
        "Late Slide 📉",
        f"A brutal late slide. You drifted down from your peak of {format_rank(peak)} to finish at {format_rank(overall)}. Those double gameweeks can be merciless!",
    )


def aggregate_season_metrics(current_season_gw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_points = 0
    overall_rank = "N/A"
    bench_pain = 0
    transfers_made = 0
    hit_cost = 0
    peak_rank = None

    if current_season_gw_data:
        last_row = current_season_gw_data[-1]
        total_points = last_row.get("total_points", 0)
        overall_rank = last_row.get("overall_rank", "N/A")

    for gw in current_season_gw_data:
        bench_pain += gw.get("points_on_bench", 0)
        transfers_made += gw.get("event_transfers", 0)
        hit_cost += gw.get("event_transfers_cost", 0)
        candidate_rank = parse_rank_value(gw.get("overall_rank"))
        if candidate_rank is not None:
            peak_rank = candidate_rank if peak_rank is None else min(peak_rank, candidate_rank)

    return {
        "total_points": total_points,
        "overall_rank": overall_rank,
        "bench_pain": bench_pain,
        "transfers_made": transfers_made,
        "hit_cost": hit_cost,
        "peak_rank": peak_rank if peak_rank is not None else "N/A",
    }


def create_wrapped_payload(
    manager_id: int,
    current_season_gw_data: List[Dict[str, Any]],
    chips_played: List[Dict[str, Any]],
    global_event_cache: Dict[int, Dict[str, Any]],
    total_players: int,
) -> Dict[str, Any]:
    metrics = aggregate_season_metrics(current_season_gw_data)
    tc_data = build_tc_analysis(chips_played, current_season_gw_data, global_event_cache, total_players)
    archetype, description = build_archetype_analysis(metrics["transfers_made"])
    persona_label, persona_desc, transfer_activity, hit_aggression = build_persona_quadrant(
        metrics["transfers_made"], metrics["hit_cost"]
    )
    finish_category, finish_desc = build_finish_analysis(metrics["overall_rank"], metrics["peak_rank"])

    return {
        "manager_id": manager_id,
        "overall_rank": format_rank(metrics["overall_rank"]),
        "peak_rank": format_rank(metrics["peak_rank"]),
        "total_points": metrics["total_points"],
        "bench_pain": metrics["bench_pain"],
        "transfers_made": metrics["transfers_made"],
        "hit_cost": metrics["hit_cost"],
        "tc_data": tc_data.dict(),
        "bb_data": {
            "played": False,
            "gw": None,
            "status": "neutral",
            "text": "Not deployed yet ⏳",
        },
        "archetype": archetype,
        "description": description,
        "persona": persona_label,
        "persona_description": persona_desc,
        "transfer_activity": round(transfer_activity, 3),
        "hit_aggression": round(hit_aggression, 3),
        "finish_category": finish_category,
        "finish_desc": finish_desc,
        "extended_ready": False,
        "season_captain_points": 0,
        "captain_curse_count": 0,
        "stellar_captain_count": 0,
        "total_players": total_players,
    }


async def build_bb_analysis(
    manager_id: int,
    chips_played: List[Dict[str, Any]],
    fpl_client: Any,
) -> ChipAnalysis:
    bb_gw = _find_chip_event(chips_played, "bboost")
    if not bb_gw:
        return ChipAnalysis(played=False, gw=None, status="neutral", text="Not deployed yet ⏳")

    try:
        live_data = await fpl_client.get_event_live(bb_gw)
        picks_data = await fpl_client.get_picks(manager_id, bb_gw)
    except Exception:
        return ChipAnalysis(
            played=True,
            gw=bb_gw,
            status="neutral",
            text="Bench Boost data could not be retrieved. Please try again later.",
        )

    live_scores = {
        element["id"]: element.get("stats", {}).get("total_points", 0)
        for element in live_data.get("elements", [])
    }
    bench_picks = [pick for pick in picks_data.get("picks", []) if pick.get("position", 0) >= 12]
    bench_points = sum(live_scores.get(pick.get("element"), 0) for pick in bench_picks)

    if bench_points < 4:
        status = "roast"
        text = f"Super Bad! Your Bench Boost in GW {bb_gw} yielded a microscopic {bench_points} points. Your subs completely ghosted you when called up! 🤡"
    elif bench_points <= 10:
        status = "neutral"
        text = f"Meh. Your Bench Boost in GW {bb_gw} brought in {bench_points} points. Not an absolute crisis, but your bench assets barely broke a sweat. 😐"
    elif bench_points <= 20:
        status = "worked"
        text = f"Solid return! Your Bench Boost in GW {bb_gw} extracted a tidy {bench_points} points from your sub assets. 📈"
    else:
        status = "worked"
        text = f"Masterclass! Your Bench Boost in GW {bb_gw} exploded for an incredible {bench_points} points! Every single sub turned up. 🚀"

    return ChipAnalysis(played=True, gw=bb_gw, status=status, text=text)


def build_live_score_map(live_data: Dict[str, Any]) -> Dict[int, int]:
    return {
        element["id"]: element.get("stats", {}).get("total_points", 0)
        for element in live_data.get("elements", [])
    }
