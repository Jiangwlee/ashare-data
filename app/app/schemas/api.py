"""API response schemas for backend routes.

Purpose: Define stable HTTP response payloads for read-only platform APIs.
"""

from __future__ import annotations

from pydantic import BaseModel


class RunResponse(BaseModel):
    run_id: str
    trade_date: str
    pipeline_name: str
    status: str
    degraded: bool


class TrendPoolDailyResponse(BaseModel):
    trade_date: str
    code: str
    name: str
    rank: int
    score_total: float
    star_rating: int
    emotion_level: int
    trade_signal: str
    is_uptrend: bool


class ThemePoolDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    theme_rank: int
    theme_strength: float | None = None
    theme_score: float | None = None
    theme_stage: str | None = None
    market_attitude: str | None = None
    core_stock_count: int
    trend_stock_count: int
    core_trend_stock_count: int
    summary: str | None = None


class ThemeStockDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    code: str
    name: str
    role: str | None = None
    is_core: bool
    rank_in_theme: int
    trend_score: float | None = None
    star_rating: int | None = None
    emotion_level: int | None = None
    comment: str | None = None
    continue_num: int | None = None
    change_rate: float | None = None
    reason_type: str | None = None
    change_tag: str | None = None


class KlineDailyResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float
    change_pct: float | None = None


class LatestTradeDateResponse(BaseModel):
    trade_date: str


class RecentTradeDatesResponse(BaseModel):
    days: int
    trade_dates: list[str]


class MarketReviewDailyResponse(BaseModel):
    trade_date: str
    run_id: str
    regime: str | None = None
    position_guidance: str | None = None
    main_themes: list[str] = []
    emerging_themes: list[str] = []
    fading_themes: list[str] = []
    summary: str | None = None
    report_markdown: str


class MarketEmotionDailyResponse(BaseModel):
    trade_date: str
    source: str
    limit_up_count: int | None = None
    limit_down_count: int | None = None
    highest_board: int
    limit_up_ladder_count: int
    board_ge_2_count: int
    board_ge_3_count: int
    board_ge_4_count: int
    advance_count: int | None = None
    decline_count: int | None = None
    flat_count: int | None = None
    blowup_rate: float | None = None
    seal_rate: float | None = None
    promotion_2to3_total: int | None = None
    promotion_2to3_success: int | None = None
    promotion_3to4_total: int | None = None
    promotion_3to4_success: int | None = None
    market_volume: float | None = None
    yesterday_limit_up_return: float | None = None
    theme_count: int
    top_theme_name: str | None = None
    top_theme_limit_up_num: int | None = None
    highest_board_3d_delta: int | None = None
    highest_board_5d_delta: int | None = None
    board_ge_3_count_3d_delta: int | None = None
    board_ge_4_count_3d_delta: int | None = None
    limit_up_count_3d_delta: int | None = None
    limit_down_count_3d_delta: int | None = None
    top_theme_limit_up_num_3d_delta: int | None = None
    heat_score: float | None = None
    risk_score: float | None = None
    emotion_score: float | None = None
    cycle_stage_hint: str | None = None
    evidence_json: dict | list | None = None


class ThemeEmotionDailyResponse(BaseModel):
    trade_date: str
    theme_name: str
    theme_rank: int
    source: str
    limit_up_num: int
    theme_change_pct: float | None = None
    sample_stock_count: int
    first_limit_count: int
    limit_back_count: int
    high_limit_count: int
    leader_names_json: list[str] | dict | None = None
    leader_board_max: int
    leader_board_count_ge_2: int
    leader_continuity_score: float | None = None
    theme_rank_3d_delta: int | None = None
    limit_up_num_3d_delta: int | None = None
    limit_up_num_5d_delta: int | None = None
    theme_change_3d_mean: float | None = None
    leader_board_max_3d_trend: int | None = None
    heat_score: float | None = None
    risk_score: float | None = None
    theme_cycle_hint: str | None = None
    evidence_json: dict | list | None = None


class StockThemeTagResponse(BaseModel):
    theme_name: str
    role_in_theme: str | None = None
    rank_in_theme: int
    theme_rank: int | None = None
    theme_cycle_hint: str | None = None
    theme_heat_score: float | None = None
    theme_limit_up_num: int | None = None
    theme_rank_3d_delta: int | None = None
    is_theme_leader: bool
    leader_names: list[str]


class ForecastYearData(BaseModel):
    year: str
    is_actual: bool
    revenue: str | None = None
    revenue_growth: str | None = None
    net_profit: str | None = None
    net_profit_growth: str | None = None
    eps: str | None = None
    bvps: str | None = None
    roe: str | None = None
    cfps: str | None = None
    pe_dynamic: str | None = None


class FundamentalRatings(BaseModel):
    buy: int = 0
    outperform: int = 0
    neutral: int = 0
    underperform: int = 0
    sell: int = 0


class FundamentalSummaryResponse(BaseModel):
    code: str
    analyst_count: int
    ratings: FundamentalRatings
    forecast_years: list[ForecastYearData]


# ── C5: Stock candidates ──────────────────────────────────────────────────────

class CandidateBarItem(BaseModel):
    date: str
    change_pct: float


class StockCandidateItem(BaseModel):
    code: str
    name: str
    source: str  # "consecutive_red" | "new_high" | "both"

    # Consecutive red fields (None when source == "new_high")
    consecutive_up_days: int | None = None
    period_gain_pct: float | None = None
    bars: list[CandidateBarItem] | None = None

    # New high fields (None when source == "consecutive_red")
    prev_high: float | None = None
    prev_high_date: str | None = None
    change_pct_today: float | None = None
    turnover_rate: float | None = None

    # Theme intersection
    primary_theme: str | None = None
    primary_theme_rank: int | None = None
    primary_theme_cycle_hint: str | None = None
    role_in_primary_theme: str | None = None
    theme_resonance: bool = False

    # One-price-board (一字板) heuristic — last bar change_pct >= 9.5%
    prev_day_yizi: bool = False


class CandidatesResponse(BaseModel):
    trade_date: str
    total: int
    consecutive_red_count: int
    new_high_count: int
    both_count: int
    candidates: list[StockCandidateItem]
