"""Cleaner functions for WTA tournament data."""

from typing import Any


def flatten_tournament(entry: dict[str, Any]) -> dict[str, Any]:
    """Flatten one raw `/tennis/tournaments/` entry into a flat row dict.

    `tournamentGroup.id` is a stable, permanent id for a tournament's venue/
    event across years (verified empirically - e.g. Indian Wells is `609` in
    both 2019 and 2025), unlike Sackmann's per-season `tourney_id`.
    """
    group = entry["tournamentGroup"]
    winners = entry.get("winners") or []
    singles_winner = (
        next(
            (
                w["singles"]["player"]["fullName"]
                for w in winners
                if (w.get("singles") or {}).get("player")
            ),
            None,
        )
        if winners
        else None
    )

    return {
        "tournament_group_id": group["id"],
        "group_name": group["name"],
        "level": entry["level"],
        "title": entry["title"],
        "year": entry["year"],
        "start_date": entry["startDate"],
        "end_date": entry["endDate"],
        "surface": entry["surface"],
        "in_outdoor": entry["inOutdoor"],
        "city": entry["city"],
        "country": entry["country"],
        "singles_draw_size": entry["singlesDrawSize"],
        "doubles_draw_size": entry["doublesDrawSize"],
        "prize_money": entry["prizeMoney"],
        "singles_champion": singles_winner,
    }
