"""Cross-source id mapping: pure matching/crosswalk logic (currently: tournaments only).

    from tennis_data_pipeline.mapper import tournaments as mapper_tournaments

See `workflows.mapper` for the I/O layer that loads clean tournament tables and
persists the resulting crosswalk/source-links CSVs under `data/mapping/`.
"""

from __future__ import annotations
