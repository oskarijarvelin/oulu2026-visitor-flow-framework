"""The quantities this package can forecast.

Until now there was exactly one: the jaskaretail visitor events, in plus out. That is a
useful number for sizing a day's staffing, but it is not the only question asked of the
data, and it answers none of them precisely. One visit makes roughly two events, so the
figure is about twice a headcount; and a counter in a doorway sees everyone who walks
through it, ticket or no ticket.

So a series is named here rather than assumed. Each one is a different real quantity
measured by a different instrument, not a rescaling of the others: at venue 1 the event
count runs about nine times the tickets sold, at venue 2 about three times. A model
trained on one says nothing about the others, which is the whole reason they are
forecast separately.

The pipeline stays single-target. ``venue_history`` copies the chosen column into
``features.TARGET`` and everything downstream reads that one name, so adding a series
here does not thread a parameter through the models, the backtest or the intervals.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Series:
    """One forecastable quantity and where it is read from."""

    series_id: str
    """Stable identifier. Names the output directory and appears in the manifest."""

    source: str
    """The processed table it comes from: ``visitors_daily`` or ``tickets_daily``."""

    column: str
    """The column in that table holding the value."""

    hourly_column: str | None
    """
    Column in ``visitors_hourly`` giving the within-day shape, or ``None`` when the
    series has no hourly measurement at all. Ticket sales are recorded per day, so
    spreading them over 24 hours would be an invention rather than a forecast, and the
    hourly file is left unwritten instead.
    """

    label_fi: str
    label_en: str

    unit_fi: str
    unit_en: str

    @property
    def has_hourly(self) -> bool:
        """Whether an hourly forecast can honestly be produced for this series."""
        return self.hourly_column is not None


VISITOR_EVENTS = Series(
    series_id="visitor_events",
    source="visitors_daily",
    column="visitors_total",
    hourly_column="visitors_total",
    label_fi="Kävijätapahtumat",
    label_en="Visitor events",
    unit_fi="kävijätapahtumaa",
    unit_en="visitor events",
)

VISITOR_ENTRIES = Series(
    series_id="visitor_entries",
    source="visitors_daily",
    column="visitors_in",
    hourly_column="visitors_in",
    label_fi="Sisäänmenot",
    label_en="Entries",
    unit_fi="sisäänmenoa",
    unit_en="entries",
)

TICKETS_SOLD = Series(
    series_id="tickets_sold",
    source="tickets_daily",
    column="tickets_sold",
    # Lipunmyynti on päivätason kirjaus, joten tunneille ei ole mitattua muotoa.
    hourly_column=None,
    label_fi="Lipunmyynti ilman ryhmiä",
    label_en="Tickets sold, groups excluded",
    unit_fi="lippua",
    unit_en="tickets",
)

ALL_SERIES: tuple[Series, ...] = (VISITOR_EVENTS, VISITOR_ENTRIES, TICKETS_SOLD)

#: The series the tool has always produced. It keeps the original output paths, so the
#: web build and every stored reader keep reading exactly what they read before.
DEFAULT_SERIES = VISITOR_EVENTS

SERIES_IDS: tuple[str, ...] = tuple(series.series_id for series in ALL_SERIES)

_BY_ID = {series.series_id: series for series in ALL_SERIES}


def series_by_id(series_id: str) -> Series:
    """Look one series up by identifier."""
    try:
        return _BY_ID[series_id]
    except KeyError:
        known = ", ".join(SERIES_IDS)
        raise KeyError(f"Unknown series: {series_id}. Known series: {known}") from None


def resolve_series(series_ids: tuple[str, ...] | None) -> tuple[Series, ...]:
    """Return the requested series in declaration order, or all of them by default."""
    if not series_ids:
        return ALL_SERIES
    wanted = {series_by_id(series_id).series_id for series_id in series_ids}
    return tuple(series for series in ALL_SERIES if series.series_id in wanted)
