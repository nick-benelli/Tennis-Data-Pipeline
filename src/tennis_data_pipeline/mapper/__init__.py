"""Cross-source id mapping: pure matching/crosswalk logic.

    from tennis_data_pipeline.mapper import tournaments as mapper_tournaments
    from tennis_data_pipeline.mapper import matches as mapper_matches

`tournaments` links tournament ids (UK <-> Sackmann <-> official id); `matches`
links individual match rows within an already-resolved tournament (Pass 1:
tournament + exact rank pair only, see `matches.build_rank_links`).

See `workflows.mapper` for the I/O layer that loads clean tournament tables and
persists the resulting crosswalk/source-links CSVs under `data/mapping/`.
"""

from __future__ import annotations
