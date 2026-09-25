"""Link tennis-data.co.uk matches (odds) to Sackmann matches (stats/IDs).

Strategy: rank-based match-level join, no fragile name parsing.
  key = (tour, winner_rank, loser_rank) within a date window
  (tennis-data `date` = actual match day; Sackmann `tourney_date` = tournament
  start, so window = [tourney_date, tourney_date + 25d]).
Rank pairs are near-unique within a window; ambiguous keys are dropped.
A name-mapping (td_name -> sackmann_id) is then distilled from aligned pairs
(majority vote) and used to link residual matches by name pair.

Output: data/parquet/match_links.parquet
  td row index, sk winner_id/loser_id, link_method (rank|name), plus join cols.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "parquet"


def main() -> None:
    td = pd.read_parquet(PARQUET / "td_matches.parquet").reset_index().rename(columns={"index": "td_id"})
    sk = pd.read_parquet(PARQUET / "sk_matches.parquet").reset_index().rename(columns={"index": "sk_id"})
    sk = sk[sk["tourney_date"] >= "2004-12-01"]

    # --- pass 1: rank-pair join within date window ---
    t = td.dropna(subset=["w_rank", "l_rank"]).copy()
    s = sk.dropna(subset=["winner_rank", "loser_rank"]).copy()
    t["w_rank"] = t["w_rank"].astype(int)
    t["l_rank"] = t["l_rank"].astype(int)
    s["winner_rank"] = s["winner_rank"].astype(int)
    s["loser_rank"] = s["loser_rank"].astype(int)

    cand = t.merge(
        s,
        left_on=["tour", "w_rank", "l_rank"],
        right_on=["tour", "winner_rank", "loser_rank"],
        how="inner",
    )
    delta = (cand["date"] - cand["tourney_date"]).dt.days
    cand = cand[(delta >= -2) & (delta <= 25)]

    # drop ambiguous: a td match matching >1 sk match or vice versa
    cand = cand[~cand.duplicated("td_id", keep=False) & ~cand.duplicated("sk_id", keep=False)]
    rank_links = cand[["td_id", "sk_id", "winner_id", "loser_id", "winner_name", "loser_name"]].copy()
    rank_links["link_method"] = "rank"

    # --- distill name map from aligned pairs (majority vote) ---
    pairs = pd.concat([
        cand[["tour", "winner", "winner_id"]].rename(columns={"winner": "td_name", "winner_id": "sk_pid"}),
        cand[["tour", "loser", "loser_id"]].rename(columns={"loser": "td_name", "loser_id": "sk_pid"}),
    ])
    vote = pairs.groupby(["tour", "td_name", "sk_pid"]).size().rename("n").reset_index()
    vote = vote.sort_values("n", ascending=False)
    top = vote.drop_duplicates(["tour", "td_name"])
    totals = vote.groupby(["tour", "td_name"])["n"].sum().rename("n_total")
    top = top.merge(totals, on=["tour", "td_name"])
    # accept mapping only if dominant (>=90% of votes, >=2 votes)
    name_map = top[(top["n"] >= 2) & (top["n"] / top["n_total"] >= 0.9)]
    name_map = name_map.set_index(["tour", "td_name"])["sk_pid"]
    name_map.rename("sk_pid").reset_index().to_parquet(PARQUET / "player_name_map.parquet", index=False)

    # --- pass 2: residual td matches linked via name map ---
    residual = td[~td["td_id"].isin(rank_links["td_id"])].copy()
    residual["w_pid"] = residual.set_index(["tour", "winner"]).index.map(name_map)
    residual["l_pid"] = residual.set_index(["tour", "loser"]).index.map(name_map)
    residual = residual.dropna(subset=["w_pid", "l_pid"])

    s2 = sk[~sk["sk_id"].isin(rank_links["sk_id"])]
    cand2 = residual.merge(
        s2,
        left_on=["tour", "w_pid", "l_pid"],
        right_on=["tour", "winner_id", "loser_id"],
        how="inner",
    )
    delta2 = (cand2["date"] - cand2["tourney_date"]).dt.days
    cand2 = cand2[(delta2 >= -2) & (delta2 <= 25)]
    cand2 = cand2[~cand2.duplicated("td_id", keep=False) & ~cand2.duplicated("sk_id", keep=False)]
    name_links = cand2[["td_id", "sk_id", "winner_id", "loser_id", "winner_name", "loser_name"]].copy()
    name_links["link_method"] = "name"

    links = pd.concat([rank_links, name_links], ignore_index=True)
    links.to_parquet(PARQUET / "match_links.parquet", index=False)

    cov = len(links) / len(td)
    print(f"td matches: {len(td)}, linked: {len(links)} ({cov:.1%}) "
          f"[rank {len(rank_links)}, name {len(name_links)}]")
    print(f"name map: {len(name_map)} td-name -> sackmann_id entries")
    # coverage by year
    linked_td = td.merge(links[["td_id"]], on="td_id")
    by_year = pd.DataFrame({
        "total": td.groupby(td["date"].dt.year).size(),
        "linked": linked_td.groupby(linked_td["date"].dt.year).size(),
    })
    by_year["pct"] = (by_year["linked"] / by_year["total"]).round(3)
    print(by_year.to_string())


if __name__ == "__main__":
    main()
