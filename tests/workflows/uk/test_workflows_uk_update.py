"""Tests for the Tennis-Data UK weekly-update workflow (`workflows.uk.update`)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tennis_data_pipeline.datasources.tennis_data_uk.checkpoint import raw_checkpoint_path
from tennis_data_pipeline.datasources.tennis_data_uk.client import (
    TennisDataUKDownloadError,
    Tour,
)
from tennis_data_pipeline.workflows.uk import update as update_module
from tennis_data_pipeline.workflows.uk.update import (
    SeasonUpdateReport,
    YearUpdateResult,
    _update_one_year,
    log_season_update_report,
    update_current_season,
)


def _write_raw_checkpoint(tour: Tour, year: int, raw_dir: Path) -> None:
    path = raw_checkpoint_path(tour, year, raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("dummy\n")


class _FakeNow:
    year = 2030

    def astimezone(self) -> _FakeNow:
        return self


class _FakeDatetime:
    @staticmethod
    def now() -> _FakeNow:
        return _FakeNow()


# --- _update_one_year ---------------------------------------------------------


def test_update_one_year_success_marks_fetched_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(update_module, "fetch_and_checkpoint_year", lambda *a, **k: None)
    monkeypatch.setattr(
        update_module, "_clean_and_write_year", lambda *a, **k: (tmp_path / "out.csv", 42)
    )
    # fetch_and_checkpoint_year is mocked to a no-op, so write the raw checkpoint by hand
    # to simulate a successful download already landing on disk.
    _write_raw_checkpoint(Tour.ATP, 2020, tmp_path)

    result = _update_one_year(Tour.ATP, 2020, client=object(), raw_dir=tmp_path, clean_dir=tmp_path)

    assert result.fetched is True
    assert result.fetch_error is None
    assert result.cleaned is True
    assert result.rows == 42
    assert result.clean_error is None


def test_update_one_year_skips_cleaning_when_no_raw_checkpoint_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch(tour: Tour, year: int, *, client: object, raw_dir: Path | None) -> None:
        raise TennisDataUKDownloadError("site down")

    monkeypatch.setattr(update_module, "fetch_and_checkpoint_year", fake_fetch)
    clean_calls: list[int] = []
    monkeypatch.setattr(
        update_module,
        "_clean_and_write_year",
        lambda *a, **k: clean_calls.append(1) or (tmp_path, 0),
    )

    result = _update_one_year(Tour.ATP, 2020, client=object(), raw_dir=tmp_path, clean_dir=tmp_path)

    assert result.fetched is False
    assert result.fetch_error == "site down"
    assert result.fetch_needs_attention is False
    assert result.cleaned is False
    assert clean_calls == []


def test_update_one_year_reprocesses_a_stale_raw_checkpoint_when_fetch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_raw_checkpoint(Tour.ATP, 2020, tmp_path)

    def fake_fetch(tour: Tour, year: int, *, client: object, raw_dir: Path | None) -> None:
        raise TennisDataUKDownloadError("site down")

    monkeypatch.setattr(update_module, "fetch_and_checkpoint_year", fake_fetch)
    monkeypatch.setattr(
        update_module, "_clean_and_write_year", lambda *a, **k: (tmp_path / "out.csv", 7)
    )

    result = _update_one_year(Tour.ATP, 2020, client=object(), raw_dir=tmp_path, clean_dir=tmp_path)

    assert result.fetched is False
    assert result.cleaned is True
    assert result.rows == 7


def test_update_one_year_marks_needs_attention_on_unexpected_fetch_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_fetch(tour: Tour, year: int, *, client: object, raw_dir: Path | None) -> None:
        raise ValueError("wrong tour data")

    monkeypatch.setattr(update_module, "fetch_and_checkpoint_year", fake_fetch)

    result = _update_one_year(Tour.ATP, 2020, client=object(), raw_dir=tmp_path, clean_dir=tmp_path)

    assert result.fetch_needs_attention is True
    assert result.fetch_error == "wrong tour data"


def test_update_one_year_records_clean_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_raw_checkpoint(Tour.ATP, 2020, tmp_path)
    monkeypatch.setattr(update_module, "fetch_and_checkpoint_year", lambda *a, **k: None)

    def fake_clean(*a: object, **k: object) -> tuple[Path, int]:
        raise ValueError("needs a known_fixes entry")

    monkeypatch.setattr(update_module, "_clean_and_write_year", fake_clean)

    result = _update_one_year(Tour.ATP, 2020, client=object(), raw_dir=tmp_path, clean_dir=tmp_path)

    assert result.cleaned is False
    assert result.clean_error == "needs a known_fixes entry"


# --- update_current_season -----------------------------------------------------


def test_update_current_season_rebuilds_tournaments_only_for_tours_with_cleaned_years(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_update_one_year(
        tour: Tour, year: int, *, client: object, raw_dir: Path | None, clean_dir: Path | None
    ) -> YearUpdateResult:
        return YearUpdateResult(tour=tour.value, year=year, fetched=True, cleaned=(tour is Tour.ATP))

    monkeypatch.setattr(update_module, "_update_one_year", fake_update_one_year)
    build_calls = []
    monkeypatch.setattr(
        update_module,
        "build_uk_tournaments",
        lambda tour, years, *, clean_dir: build_calls.append((tour, list(years))) or (Path("/x"), 1, 0),
    )

    report = update_current_season(tours=[Tour.ATP, Tour.WTA], years=[2020], client=object())

    assert build_calls == [(Tour.ATP, [2020])]
    assert report.tournament_tables == {"atp": Path("/x")}
    assert report.needs_attention is False


def test_update_current_season_records_tournament_rebuild_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        update_module,
        "_update_one_year",
        lambda tour, year, *, client, raw_dir, clean_dir: YearUpdateResult(
            tour=tour.value, year=year, cleaned=True
        ),
    )

    def fake_build(tour: Tour, years: list[int], *, clean_dir: Path | None) -> tuple[Path, int, int]:
        raise ValueError("bad rebuild")

    monkeypatch.setattr(update_module, "build_uk_tournaments", fake_build)

    report = update_current_season(tours=[Tour.ATP], years=[2020], client=object())

    assert report.tournament_errors == {"atp": "bad rebuild"}
    assert report.needs_attention is True


def test_update_current_season_defaults_years_to_the_current_and_previous_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(update_module, "datetime", _FakeDatetime)
    calls: list[int] = []

    def fake_update_one_year(
        tour: Tour, year: int, *, client: object, raw_dir: Path | None, clean_dir: Path | None
    ) -> YearUpdateResult:
        calls.append(year)
        return YearUpdateResult(tour=tour.value, year=year)

    monkeypatch.setattr(update_module, "_update_one_year", fake_update_one_year)

    update_current_season(tours=[Tour.ATP], client=object())

    assert sorted(set(calls)) == [2029, 2030]


# --- SeasonUpdateReport.needs_attention -----------------------------------------


def test_needs_attention_is_false_when_everything_is_clean() -> None:
    report = SeasonUpdateReport(results=[YearUpdateResult(tour="atp", year=2020, cleaned=True)])

    assert report.needs_attention is False


def test_needs_attention_is_true_for_a_clean_error() -> None:
    report = SeasonUpdateReport(results=[YearUpdateResult(tour="atp", year=2020, clean_error="oops")])

    assert report.needs_attention is True


def test_needs_attention_is_true_for_an_unexpected_fetch_error() -> None:
    report = SeasonUpdateReport(
        results=[YearUpdateResult(tour="atp", year=2020, fetch_needs_attention=True)]
    )

    assert report.needs_attention is True


def test_needs_attention_ignores_plain_fetch_failures() -> None:
    report = SeasonUpdateReport(
        results=[YearUpdateResult(tour="atp", year=2020, fetch_error="site down")]
    )

    assert report.needs_attention is False


def test_needs_attention_is_true_for_a_tournament_rebuild_error() -> None:
    report = SeasonUpdateReport(
        results=[YearUpdateResult(tour="atp", year=2020, cleaned=True)],
        tournament_errors={"atp": "bad rebuild"},
    )

    assert report.needs_attention is True


# --- log_season_update_report ---------------------------------------------------


def test_log_season_update_report_does_not_raise_for_every_branch() -> None:
    report = SeasonUpdateReport(
        results=[
            YearUpdateResult(tour="atp", year=2018, clean_error="oops"),
            YearUpdateResult(tour="atp", year=2019, fetch_needs_attention=True, fetch_error="weird"),
            YearUpdateResult(tour="atp", year=2020, cleaned=True, rows=10, fetched=True),
            YearUpdateResult(tour="atp", year=2021, cleaned=True, rows=5, fetched=False),
            YearUpdateResult(tour="atp", year=2022, fetch_error="site down"),
            YearUpdateResult(tour="atp", year=2023),
        ],
        tournament_tables={"atp": Path("/x")},
        tournament_errors={"wta": "bad rebuild"},
    )

    log_season_update_report(report)
