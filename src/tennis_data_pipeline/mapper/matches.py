"""Cross-source match-level linking: Tennis-Data UK <-> Sackmann (Pass 1 only).

Pure functions over already-clean match-level `DataFrame`s - no file I/O here
(see `workflows.mapper` for that layer, following the `mapper.tournaments`
precedent).

Pass 1 methodology (tournament-blocked exact rank pair):

    UK match row                    Sackmann match row
         |                                 |
    official_tournament_id  <----(tournament_mapper)---->  official_tournament_id
         |                                 |
         +--------- year, tour, winner_rank, loser_rank ---+
                            |
                    candidate match
                            |
              exactly one on both sides?
                    /              \\
                 yes                no
                  |                  |
          accepted link      ambiguous candidate

Rows that never produce a candidate (missing tournament id, missing rank, or
no counterpart) fall out as unmatched. Nothing here does player-name fuzzy
matching or a date-window join - see `docs/My-Notes/link_td_sackmann.py` /
`Link-UK-Sackmann.ipynb` for the later passes this is designed to feed into.
"""

from __future__ import annotations

import pandas as pd

MATCH_METHOD_TOURNAMENT_RANK_UNIQUE = "tournament_rank_unique"

# The blocking + exact-match key shared by both sides once official_tournament_id
# is attached and Sackmann's source_year has been aliased to "year".
RANK_CANDIDATE_KEY_COLUMNS = ["year", "tour", "official_tournament_id", "winner_rank", "loser_rank"]

CROSSWALK_COLUMNS = [
    "source_match_key",
    "canonical_match_key",
    "official_tournament_id",
    "year",
    "tour",
    "winner_rank",
    "loser_rank",
    "winner_id",
    "loser_id",
    "match_method",
    "review_flag",
    "source_candidate_count",
    "canonical_candidate_count",
    "round_agrees",
    "winner_rank_points_diff",
    "loser_rank_points_diff",
]


def attach_tournament_ids(
    matches: pd.DataFrame,
    tournament_mapper: pd.DataFrame,
    *,
    source: str,
    match_tournament_col: str,
    year_col: str,
) -> pd.DataFrame:
    """Attach `official_tournament_id` to a source's match rows.

    Looks up `tournament_mapper` rows where `source` equals `source`, keyed by
    (`year_col`, `match_tournament_col`) in `matches` against Sackmann's/`UK`s
    (`year`, `source_tournament_id`) in `tournament_mapper`. Every other column
    in `matches` is left unchanged - this only adds `official_tournament_id`.

    Raises a `pandas.errors.MergeError` (via `validate="many_to_one"`) if
    `tournament_mapper` has more than one `official_tournament_id` for the
    same (`year_col`, `match_tournament_col`) combination.
    """
    mapper = (
        tournament_mapper.loc[
            tournament_mapper["source"].eq(source),
            ["year", "source_tournament_id", "official_tournament_id"],
        ]
        .drop_duplicates()
        .rename(columns={"year": year_col, "source_tournament_id": match_tournament_col})
    )

    return matches.merge(
        mapper,
        on=[year_col, match_tournament_col],
        how="left",
        validate="many_to_one",
    )


def add_sackmann_match_key(sackmann_df: pd.DataFrame) -> pd.DataFrame:
    """Add a stable `canonical_match_key` = `tourney_id` + "_" + `match_num` column."""
    sackmann_df = sackmann_df.copy()
    sackmann_df["canonical_match_key"] = (
        sackmann_df["tourney_id"].astype(str) + "_" + sackmann_df["match_num"].astype(str)
    )
    return sackmann_df


def generate_rank_candidates(uk_df: pd.DataFrame, sackmann_df: pd.DataFrame) -> pd.DataFrame:
    """Generate match-link candidates by blocking on tournament + exact rank pair.

    Both inputs must already carry `official_tournament_id` (see
    `attach_tournament_ids`); `sackmann_df` gets `canonical_match_key` added if
    missing. Rows missing `official_tournament_id`, `winner_rank`, or
    `loser_rank` are excluded on both sides - they can't be rank-matched.

    This is a plain vectorized inner merge, so a source row can legitimately
    appear against more than one Sackmann row (and vice versa); resolving
    that ambiguity is `classify_rank_candidates`'s job, not this one.
    """
    if "canonical_match_key" not in sackmann_df.columns:
        sackmann_df = add_sackmann_match_key(sackmann_df)

    uk_ranked = uk_df.dropna(subset=["official_tournament_id", "winner_rank", "loser_rank"]).copy()
    sackmann_ranked = sackmann_df.dropna(
        subset=["official_tournament_id", "winner_rank", "loser_rank"]
    ).copy()
    sackmann_ranked["year"] = sackmann_ranked["source_year"]

    for frame in (uk_ranked, sackmann_ranked):
        frame["winner_rank"] = frame["winner_rank"].astype("Int64")
        frame["loser_rank"] = frame["loser_rank"].astype("Int64")

    return uk_ranked.merge(
        sackmann_ranked,
        on=RANK_CANDIDATE_KEY_COLUMNS,
        how="inner",
        suffixes=("_uk", "_sk"),
    )


def classify_rank_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    """Add uniqueness + supporting-evidence diagnostics to rank-pair candidates.

    - `source_candidate_count` / `canonical_candidate_count`: how many
      counterpart rows each side's match key maps to among these candidates.
    - `is_unique`: True only when both counts equal 1 - the sole condition
      under which a candidate is safe to accept.
    - `round_agrees`, `winner_rank_points_diff`, `loser_rank_points_diff`:
      corroborating evidence only; they never filter/reject a candidate here.
    """
    candidates = candidates.copy()

    candidates["source_candidate_count"] = candidates.groupby("source_match_key")[
        "canonical_match_key"
    ].transform("nunique")
    candidates["canonical_candidate_count"] = candidates.groupby("canonical_match_key")[
        "source_match_key"
    ].transform("nunique")
    candidates["is_unique"] = candidates["source_candidate_count"].eq(1) & candidates[
        "canonical_candidate_count"
    ].eq(1)

    candidates["round_agrees"] = candidates["round_uk"] == candidates["round_sk"]
    candidates["winner_rank_points_diff"] = (
        candidates["winner_rank_points_uk"] - candidates["winner_rank_points_sk"]
    ).abs()
    candidates["loser_rank_points_diff"] = (
        candidates["loser_rank_points_uk"] - candidates["loser_rank_points_sk"]
    ).abs()

    return candidates


def build_rank_links(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    tournament_mapper_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Pass 1 (tournament-blocked exact rank pair) match linking end to end.

    Returns `(accepted_links, ambiguous_candidates, unmatched_uk_rows)`:

    - `accepted_links`: the `CROSSWALK_COLUMNS` crosswalk - one row per
      uk<->sackmann pair, `source_match_key` and `canonical_match_key` are
      each unique across the frame, `match_method` is always
      `MATCH_METHOD_TOURNAMENT_RANK_UNIQUE`.
    - `ambiguous_candidates`: classified candidates where either side matched
      more than one counterpart - kept for a later resolution pass, never
      silently dropped.
    - `unmatched_uk_rows`: `uk_df` rows (identified by `source_match_key`)
      that produced no rank-pair candidate at all, e.g. missing tournament
      id, missing rank, or no counterpart Sackmann row.

    Raises `ValueError` if `source_match_key` isn't unique in `uk_df`, or the
    derived `canonical_match_key` isn't unique in `sackmann_df`.
    """
    if uk_df["source_match_key"].duplicated().any():
        raise ValueError("uk_df['source_match_key'] must be unique")

    sackmann_df = add_sackmann_match_key(sackmann_df)
    if sackmann_df["canonical_match_key"].duplicated().any():
        raise ValueError("sackmann_df's derived canonical_match_key must be unique")

    uk_linked = attach_tournament_ids(
        uk_df,
        tournament_mapper_df,
        source="tennis_data_uk",
        match_tournament_col="source_event_key",
        year_col="year",
    )
    sackmann_linked = attach_tournament_ids(
        sackmann_df,
        tournament_mapper_df,
        source="sackmann",
        match_tournament_col="tourney_id",
        year_col="source_year",
    )

    candidates = classify_rank_candidates(generate_rank_candidates(uk_linked, sackmann_linked))

    accepted = candidates.loc[candidates["is_unique"]].copy()
    accepted["match_method"] = MATCH_METHOD_TOURNAMENT_RANK_UNIQUE
    accepted["review_flag"] = False
    if (
        accepted["source_match_key"].duplicated().any()
        or accepted["canonical_match_key"].duplicated().any()
    ):
        raise AssertionError("accepted rank links must be 1:1 on both match keys")
    accepted = accepted[CROSSWALK_COLUMNS]

    ambiguous = candidates.loc[~candidates["is_unique"]].copy()

    unmatched_uk_rows = uk_linked.loc[
        ~uk_linked["source_match_key"].isin(candidates["source_match_key"])
    ].copy()

    return accepted, ambiguous, unmatched_uk_rows
