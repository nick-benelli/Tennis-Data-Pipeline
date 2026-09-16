# Packages
import os

from ...config import settings

# Tennis-Data.co.uk directory
PACK_DIR = os.path.dirname(os.path.realpath(__file__))

# GitHub mirror of scraped results (fallback data source), overridable via env vars / .env
# TODO: not wired into TennisDataUKClient yet; dead code until a mirror-based loader exists.
GITHUB_USER = settings.tennis_data_uk.github_user
GITHUB_REPO = settings.tennis_data_uk.github_repo
GITHUB_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/{user}/{repo}/main/data/{tour}/tennis-data-uk/{tour}_singles_results_{year}.csv"
)


# Also currently unused by cleaning.py/client.py.
DATE_COL = 'DATE'
TOURNEY_COLS = [
    'ATP', 'WTA', 'TournamentNumber', 'Location', 'Tournament', 'Series', 'Tier', 'Court', 'Surface'
]


COLUMN_MAP = {
    # ATP's tournament number and WTA's tournament number are the same concept
    # under different source column names; both normalize to TournamentNumber.
    "ATP" : "TournamentNumber", 
    "WTA" : "TournamentNumber", 
    # ATP's Series and WTA's Tier both describe tournament category/level;
    # intentionally normalized to one canonical name.
    "Tier" : "Series", 
    "Series" : "Series", 
    "Winner" : "winner_Name", 
    "Loser" : "loser_Name", 
    "WRank" : "winner_Rank", 
    "LRank" : "loser_Rank", 
    "WPts" : "winner_Pts", 
    "LPts" : "loser_Pts",
    "W1" : "winner_Set1", 
    "L1" : "loser_Set1", 
    "W2" : "winner_Set2", 
    "L2" : "loser_Set2", 
    "W3" : "winner_Set3", 
    "L3" : "loser_Set3", 
    "W4" : "winner_Set4", 
    "L4" : "loser_Set4", 
    "W5" : "winner_Set5", 
    "L5" : "loser_Set5", 
    "Wsets" : "winner_Sets",
    "Lsets" : "loser_Sets", 

    # Odds
    "B365W" : "winner_B365_odds", 
    "B365L" : "loser_B365_odds", 
    "B&WW" : "winner_B&W_odds", 
    "B&WL" : "loser_B&W_odds", 
    "CBW" : "winner_CB_odds", 
    "CBL" : "loser_CB_odds", 
    "EXW" : "winner_EX_odds", 
    "EXL" : "loser_EX_odds", 
    "LBW" : "winner_LB_odds", 
    "LBL" : "loser_LB_odds", 
    "GBW" : "winner_GB_odds", 
    "GBL" : "loser_GB_odds", 
    "IWW" : "winner_IW_odds", 
    "IWL" : "loser_IW_odds", 
    "PSW" : "winner_PS_odds", 
    "PSL" : "loser_PS_odds", 
    "SBW" : "winner_SB_odds", 
    "SBL" : "loser_SB_odds", 
    "SJW" : "winner_SJ_odds", 
    "SJL" : "loser_SJ_odds", 
    "UBW" : "winner_UB_odds",
    "UBL" : "loser_UB_odds", 

    # Average and Max Odds
    "MaxW" : "winner_Max_odds", 
    "MaxL" : "loser_Max_odds",
    "AvgW" : "winner_Avg_odds", 
    "AvgL" : "loser_Avg_odds"
}

# Canonical (post-COLUMN_MAP) columns that should hold numeric values. Used to
# backfill columns missing due to schema drift across seasons (with NaN) and
# to coerce them to numeric dtype. Never used to substitute one bookmaker's
# odds for another's.
NUMERIC_COLUMNS = [
    "winner_Rank",
    "loser_Rank",
    "winner_Pts",
    "loser_Pts",
    "winner_Set1",
    "loser_Set1",
    "winner_Set2",
    "loser_Set2",
    "winner_Set3",
    "loser_Set3",
    "winner_Set4",
    "loser_Set4",
    "winner_Set5",
    "loser_Set5",
    "winner_Sets",
    "loser_Sets",
    "winner_B365_odds",
    "loser_B365_odds",
    "winner_B&W_odds",
    "loser_B&W_odds",
    "winner_CB_odds",
    "loser_CB_odds",
    "winner_EX_odds",
    "loser_EX_odds",
    "winner_LB_odds",
    "loser_LB_odds",
    "winner_GB_odds",
    "loser_GB_odds",
    "winner_IW_odds",
    "loser_IW_odds",
    "winner_PS_odds",
    "loser_PS_odds",
    "winner_SB_odds",
    "loser_SB_odds",
    "winner_SJ_odds",
    "loser_SJ_odds",
    "winner_UB_odds",
    "loser_UB_odds",
    "winner_Max_odds",
    "loser_Max_odds",
    "winner_Avg_odds",
    "loser_Avg_odds",
]