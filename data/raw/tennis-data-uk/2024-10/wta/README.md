# Known-bad file (deleted)

`wta_singles_results_2024.csv` actually contained 2024 **ATP** match data (wrong
tour entirely - header used `ATP`/`Series` and included best-of-5 set columns,
and the player names were ATP players). It has been deleted; re-download the
real 2024 WTA season from tennis-data.co.uk into
`data/raw/tennis-data-uk/wta/wta_singles_results_2024.csv` (the Stage-2
checkpoint convention) before cleaning that season. See
`docs/tennis-data-uk-pipeline-plan.md`.

All other years (2007-2023) were verified and moved to
`data/raw/tennis-data-uk/wta/` (the new Stage-2 checkpoint convention).
