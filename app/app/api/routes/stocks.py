"""Read-only per-stock research routes.

Purpose: Expose aggregated per-stock research data for pi-trader consumers.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.db.session import init_db, open_session
from app.models.new_high_daily import NewHighDaily
from app.models.red_window_daily import RedWindowDaily
from app.models.theme_emotion_daily import ThemeEmotionDaily
from app.models.theme_member_stock import ThemeMemberStock
from app.models.theme_stock_daily import ThemeStockDaily
from app.schemas.api import (
    CandidateBarItem,
    CandidatesResponse,
    ForecastYearData,
    FundamentalRatings,
    FundamentalSummaryResponse,
    StockCandidateItem,
    StockThemeTagResponse,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])

_ROLE_MAP = {
    "leader": "leader",
    "core": "core",
    "follower": "member",
    "edge": "edge",
}


def _extract_leader_names(leader_names_json: list | dict | None) -> list[str]:
    if isinstance(leader_names_json, list):
        return [str(n) for n in leader_names_json if n]
    if isinstance(leader_names_json, dict):
        return [str(v) for v in leader_names_json.values() if v]
    return []


@router.get("/themes/{code}/{trade_date}", response_model=list[StockThemeTagResponse])
def get_stock_themes(code: str, trade_date: str) -> list[StockThemeTagResponse]:
    """Get all theme tags for a stock on a given trade date.

    Returns the themes the stock belongs to, with heat and cycle data joined
    from theme_emotion_daily. Returns [] if the stock has no theme records.
    """
    init_db()
    with open_session() as session:
        stock_rows = (
            session.query(ThemeStockDaily)
            .filter(ThemeStockDaily.code == code, ThemeStockDaily.trade_date == trade_date)
            .order_by(ThemeStockDaily.rank_in_theme.asc())
            .all()
        )

        if not stock_rows:
            return []

        theme_names = [r.theme_name for r in stock_rows]
        emotion_rows = (
            session.query(ThemeEmotionDaily)
            .filter(
                ThemeEmotionDaily.trade_date == trade_date,
                ThemeEmotionDaily.theme_name.in_(theme_names),
            )
            .all()
        )
        emotion_by_theme: dict[str, ThemeEmotionDaily] = {r.theme_name: r for r in emotion_rows}

        result: list[StockThemeTagResponse] = []
        for sr in stock_rows:
            er = emotion_by_theme.get(sr.theme_name)
            role = _ROLE_MAP.get(sr.role or "", sr.role)
            leader_names = _extract_leader_names(er.leader_names_json if er else None)
            result.append(
                StockThemeTagResponse(
                    theme_name=sr.theme_name,
                    role_in_theme=role,
                    rank_in_theme=sr.rank_in_theme,
                    theme_rank=er.theme_rank if er else None,
                    theme_cycle_hint=er.theme_cycle_hint if er else None,
                    theme_heat_score=er.heat_score if er else None,
                    theme_limit_up_num=er.limit_up_num if er else None,
                    theme_rank_3d_delta=er.theme_rank_3d_delta if er else None,
                    is_theme_leader=(sr.role == "leader"),
                    leader_names=leader_names,
                )
            )
        return result


@router.get("/fundamental/{code}", response_model=FundamentalSummaryResponse)
def get_stock_fundamental(code: str) -> FundamentalSummaryResponse:
    """Fetch analyst consensus forecasts and historical financials for a stock.

    Live-fetches from THS worth page (no DB dependency). Returns 6 years of data:
    3 historical actuals + 3 analyst forecast years.
    """
    from ashare_data.fetchers.ths_worth import fetch_worth_data

    data = fetch_worth_data(code)
    if not data:
        raise HTTPException(status_code=503, detail="Failed to fetch fundamental data from THS")

    ratings_raw = data.get("ratings", {})
    ratings = FundamentalRatings(
        buy=ratings_raw.get("buy", 0),
        outperform=ratings_raw.get("outperform", 0),
        neutral=ratings_raw.get("neutral", 0),
        underperform=ratings_raw.get("underperform", 0),
        sell=ratings_raw.get("sell", 0),
    )

    years: list[str] = data.get("years", [])
    is_actual: list[bool] = data.get("is_actual", [])
    metrics: dict = data.get("metrics", {})

    forecast_years: list[ForecastYearData] = []
    for i, year in enumerate(years):
        actual_flag = is_actual[i] if i < len(is_actual) else False

        def _get(key: str) -> str | None:
            vals = metrics.get(key)
            if vals and i < len(vals):
                v = vals[i]
                return v if v and v != "--" else None
            return None

        forecast_years.append(
            ForecastYearData(
                year=year,
                is_actual=actual_flag,
                revenue=_get("revenue"),
                revenue_growth=_get("revenue_growth"),
                net_profit=_get("net_profit"),
                net_profit_growth=_get("net_profit_growth"),
                eps=_get("eps"),
                bvps=_get("bvps"),
                roe=_get("roe"),
                cfps=_get("cfps"),
                pe_dynamic=_get("pe_dynamic"),
            )
        )

    return FundamentalSummaryResponse(
        code=code,
        analyst_count=data.get("analyst_count", 0),
        ratings=ratings,
        forecast_years=forecast_years,
    )


@router.get("/candidates/{trade_date}", response_model=CandidatesResponse)
def get_stock_candidates(
    trade_date: str,
    min_consecutive_days: int = Query(5, ge=1),
    top_n_themes: int = Query(10, ge=1, le=50),
    exclude_yizi: bool = Query(True),
    include_new_high: bool = Query(True),
) -> CandidatesResponse:
    """Get stock candidates for a trade date by merging consecutive-red and new-high pools.

    Enriches each candidate with theme intersection data (primary_theme, theme_resonance)
    and a one-price-board (yizi) heuristic based on the last bar's change_pct.

    Query params:
        min_consecutive_days: Minimum red candles required (default 5).
        top_n_themes: Number of top-ranked themes to consider for resonance (default 10).
        exclude_yizi: Exclude candidates whose last bar looks like a yizi (default True).
        include_new_high: Include new all-time high stocks as candidates (default True).
    """
    trade_date_obj = date.fromisoformat(trade_date)

    init_db()
    with open_session() as session:
        # 1. Consecutive-red candidates: deduplicate by code, prefer higher window_days
        red_rows = (
            session.query(RedWindowDaily)
            .filter(
                RedWindowDaily.trade_date == trade_date,
                RedWindowDaily.red_count >= min_consecutive_days,
            )
            .order_by(RedWindowDaily.window_days.desc(), RedWindowDaily.rank.asc())
            .all()
        )
        red_by_code: dict[str, RedWindowDaily] = {}
        for row in red_rows:
            if row.code not in red_by_code:
                red_by_code[row.code] = row

        # 2. New-high candidates
        new_high_by_code: dict[str, NewHighDaily] = {}
        if include_new_high:
            nh_rows = (
                session.query(NewHighDaily)
                .filter(NewHighDaily.trade_date == trade_date)
                .all()
            )
            new_high_by_code = {row.code: row for row in nh_rows}

        # 3. Merge by code → source
        all_codes = set(red_by_code) | set(new_high_by_code)

        # 4. Top-N themes for resonance check (trade_date is DATE column, use date object)
        top_themes = (
            session.query(ThemeEmotionDaily)
            .filter(ThemeEmotionDaily.trade_date == trade_date_obj)
            .order_by(ThemeEmotionDaily.theme_rank.asc())
            .limit(top_n_themes)
            .all()
        )
        top_theme_names: set[str] = {t.theme_name for t in top_themes}
        theme_rank_map: dict[str, int] = {t.theme_name: t.theme_rank for t in top_themes}
        theme_cycle_map: dict[str, str | None] = {
            t.theme_name: t.theme_cycle_hint for t in top_themes
        }

        # 5. Reverse-lookup via theme_member_stock (full 64k-row coverage).
        #    Query: which candidates appear in any of the top-N themes?
        member_rows = (
            session.query(ThemeMemberStock.code, ThemeMemberStock.concept_name)
            .filter(
                ThemeMemberStock.concept_name.in_(list(top_theme_names)),
                ThemeMemberStock.code.in_(list(all_codes)),
            )
            .all()
        )
        # code → list of theme_names (all within top_n)
        stock_themes: dict[str, list[str]] = {}
        for code_val, theme_name in member_rows:
            stock_themes.setdefault(code_val, []).append(theme_name)

    # 6. Build candidate items
    items: list[StockCandidateItem] = []
    for code in all_codes:
        red = red_by_code.get(code)
        nh = new_high_by_code.get(code)

        if red and nh:
            source = "both"
        elif red:
            source = "consecutive_red"
        else:
            source = "new_high"

        # Compute bars and yizi from red window
        bars: list[CandidateBarItem] | None = None
        prev_day_yizi = False
        if red:
            raw_bars: list[dict] = red.bars_json or []
            bars = [CandidateBarItem(date=b["date"], change_pct=b["change_pct"]) for b in raw_bars]
            if raw_bars:
                prev_day_yizi = raw_bars[-1]["change_pct"] >= 9.5

        # Apply exclude_yizi filter
        if exclude_yizi and prev_day_yizi:
            continue

        # Theme intersection (stock_themes only contains top-N theme names)
        themes_for_code = stock_themes.get(code, [])
        primary_theme: str | None = None
        primary_theme_rank: int | None = None
        primary_theme_cycle: str | None = None
        theme_resonance = len(themes_for_code) > 0

        for t_name in themes_for_code:
            t_rank = theme_rank_map[t_name]
            if primary_theme_rank is None or t_rank < primary_theme_rank:
                primary_theme = t_name
                primary_theme_rank = t_rank
                primary_theme_cycle = theme_cycle_map.get(t_name)

        name = red.name if red else (nh.name if nh else code)

        items.append(
            StockCandidateItem(
                code=code,
                name=name,
                source=source,
                # consecutive_red fields
                consecutive_up_days=red.red_count if red else None,
                period_gain_pct=red.gain_pct if red else None,
                bars=bars,
                # new_high fields
                prev_high=nh.prev_high if nh else None,
                prev_high_date=nh.prev_high_date if nh else None,
                change_pct_today=nh.change_pct if nh else None,
                turnover_rate=nh.turnover_rate if nh else None,
                # theme intersection
                primary_theme=primary_theme,
                primary_theme_rank=primary_theme_rank,
                primary_theme_cycle_hint=primary_theme_cycle,
                role_in_primary_theme=None,
                theme_resonance=theme_resonance,
                prev_day_yizi=prev_day_yizi,
            )
        )

    # Sort: theme_resonance first, then by consecutive_up_days desc, then code
    items.sort(key=lambda x: (not x.theme_resonance, -(x.consecutive_up_days or 0), x.code))

    consecutive_red_count = sum(1 for x in items if x.source in ("consecutive_red", "both"))
    new_high_count = sum(1 for x in items if x.source in ("new_high", "both"))
    both_count = sum(1 for x in items if x.source == "both")

    return CandidatesResponse(
        trade_date=trade_date,
        total=len(items),
        consecutive_red_count=consecutive_red_count,
        new_high_count=new_high_count,
        both_count=both_count,
        candidates=items,
    )
