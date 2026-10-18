"""Division-aware, recency-weighted scouting ratings from verified PLP standings."""
from __future__ import annotations

from math import tanh


def metric(row: dict | None, name: str) -> float | None:
    if not row or not row.get("matches") or row.get(name) is None:
        return None

    return float(row[name]) / float(row["matches"])


def season_strength(row: dict | None) -> float | None:
    if not row or not row.get("matches"):
        return None

    required = ("points", "gf", "ga")
    if any(row.get(field) is None for field in required):
        return None

    tier = int(row.get("tier") or 1)
    baseline = 62.0 if tier == 1 else 39.0
    points_fraction = float(row["points"]) / (3 * float(row["matches"]))
    goal_difference = (float(row["gf"]) - float(row["ga"])) / float(row["matches"])
    goals_for = float(row["gf"]) / float(row["matches"])
    goals_against = float(row["ga"]) / float(row["matches"])
    sample = min(1.0, float(row["matches"]) / 12.0)

    position = row.get("position")
    league_size = int(row.get("league_size") or 16)
    position_bonus = (
        3.5 * (1 - 2 * (int(position) - 1) / max(1, league_size - 1))
        if position is not None else 0.0
    )

    performance = (
        28 * (points_fraction - 0.5)
        + 9 * tanh(goal_difference / 2.7)
        + 3 * tanh((goals_for - 3) / 2)
        + 3 * tanh((2.7 - goals_against) / 2)
        + position_bonus
    )

    return max(0.0, min(100.0, baseline + performance * sample))


def team_strength(hall: dict | None, orlik: dict | None) -> float | None:
    recent = season_strength(orlik)
    previous = season_strength(hall)

    if recent is None and previous is None:
        return None

    if recent is None:
        tier_baseline = 62 if int(hall.get("tier") or 1) == 1 else 39
        return round(0.85 * previous + 0.15 * tier_baseline, 1)

    if previous is None:
        tier_baseline = 62 if int(orlik.get("tier") or 1) == 1 else 39
        return round(0.9 * recent + 0.1 * tier_baseline, 1)

    return round(0.65 * recent + 0.35 * previous, 1)


def evidence(hall: dict | None, orlik: dict | None) -> dict:
    return {
        "orlik": round(season_strength(orlik), 1) if season_strength(orlik) is not None else None,
        "hala": round(season_strength(hall), 1) if season_strength(hall) is not None else None,
        "model": "division_adjusted_2026_v2",
        "benchmark": "Points, goal difference, attack, defense, league position, tier, sample size",
    }
