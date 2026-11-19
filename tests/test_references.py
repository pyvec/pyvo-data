"""Checks that JSON Schema cannot express: cross-file references, uniqueness.

These mirror what the consumer, pyvocz, enforces when it loads the data; see
`Root.load`, `Series.load` and `Event.load` in pyvocz/data.py, and
pyvocz/typecheck.py for the type checks. Missing or mistyped fields are
covered by schema.yaml (see BREAKAGES in test_schema.py).
If pyvocz gains a load-time rule, add it here.
"""
import copy

from dateutil import rrule


def _events(data):
    for series_slug, series in sorted(data['series'].items()):
        for event_slug, event in sorted(series['events'].items()):
            yield series_slug, event_slug, event


def _first_event(data, **requires):
    for _, _, event in _events(data):
        if all((key in event) == wanted for key, wanted in requires.items()):
            return event
    raise LookupError(f'no event with {requires}')


def _venue_slugs(data):
    return [
        (city, slug)
        for city, content in sorted(data['cities'].items())
        for slug in sorted(content.get('venues', {}))
    ]


def _rrule_problems(source, recurrence):
    """Problems with a series' recurrence block, as a list of messages"""
    if 'rrule' not in recurrence:
        return [f'{source}: recurrence has no rrule']
    try:
        rrule.rrulestr(recurrence['rrule'])
    except Exception as e:
        # dateutil raises ValueError for bad syntax, but other exception
        # types for odd values (e.g. a list): report them all, don't crash
        return [f"{source}: bad rrule {recurrence['rrule']!r}: {e}"]
    return []


def find_problems(data):
    """Return a list of human-readable rule violations (empty means OK)"""
    problems = []

    if data['meta'].get('version') != 2:
        problems.append(
            f"meta.yaml: unsupported version {data['meta'].get('version')!r}"
            " (can only load version 2)")

    cities = data['cities']
    venues = {}
    for city, slug in _venue_slugs(data):
        if slug in venues:
            problems.append(
                f'duplicate venue slug: {slug} '
                f'(in {venues[slug]} and {city})')
        venues[slug] = city

    event_count = 0
    for series_slug, series_dir in sorted(data['series'].items()):
        if 'series' not in series_dir:
            problems.append(f'series/{series_slug}: missing series.yaml')
            continue
        series = series_dir['series']
        if series.get('city') not in cities:
            problems.append(
                f"{series['_source']}: unknown city {series.get('city')!r}")
        recurrence = series.get('recurrence')
        if recurrence:
            problems.extend(_rrule_problems(series['_source'], recurrence))
        for event in series_dir.get('events', {}).values():
            event_count += 1
            city = event.get('city')
            if city is None:
                problems.append(f"{event['_source']}: missing city")
            elif city not in cities:
                problems.append(f"{event['_source']}: unknown city {city!r}")
            venue = event.get('venue')
            if venue and venue not in venues:
                problems.append(
                    f"{event['_source']}: unknown venue {venue!r}")

    # Sanity check inherited from the old pyvodb-based test: pyvocz itself
    # would load an empty data set.
    if not event_count:
        problems.append('no events found')
    return problems


def test_real_data_has_no_problems(loaded_data):
    assert find_problems(loaded_data) == []


def test_wrong_version(data):
    data['meta']['version'] = 3
    assert any('version' in p for p in find_problems(data))


def test_duplicate_venue_slug_across_cities(data):
    city, slug = _venue_slugs(data)[0]
    other = next(c for c in sorted(data['cities']) if c != city)
    data['cities'][other].setdefault('venues', {})[slug] = copy.deepcopy(
        data['cities'][city]['venues'][slug])
    assert any(f'duplicate venue slug: {slug}' in p
               for p in find_problems(data))


def test_unknown_event_city(data):
    _first_event(data)['city'] = 'nowhere'
    assert any('unknown city' in p and 'nowhere' in p
               for p in find_problems(data))


def test_unknown_event_venue(data):
    _first_event(data)['venue'] = 'no-such-venue'
    assert any('unknown venue' in p and 'no-such-venue' in p
               for p in find_problems(data))


def test_unknown_series_city(data):
    slug = sorted(data['series'])[0]
    data['series'][slug]['series']['city'] = 'nowhere'
    assert any('unknown city' in p and slug in p
               for p in find_problems(data))


def test_bad_rrule(data):
    slug = next(s for s, c in sorted(data['series'].items())
                if 'recurrence' in c['series'])
    data['series'][slug]['series']['recurrence']['rrule'] = 'FREQ=NOPE'
    assert any('rrule' in p and slug in p for p in find_problems(data))


def test_no_events(data):
    for series in data['series'].values():
        series['events'] = {}
    assert any('no events' in p for p in find_problems(data))


def test_two_events_same_month_allowed(data):
    # pyvocz's URL slug is YYYY-MM, so its event page 404s for such events,
    # but its loader accepts them and the data has them (ostrava-pyvo 2023-08).
    # The data is validated as is: do not add a uniqueness rule.
    series_slug, event_slug, event = next(_events(data))
    twin = copy.deepcopy(event)
    data['series'][series_slug]['events'][event_slug + '-twin'] = twin
    assert find_problems(data) == []


def test_series_without_recurrence_ok(data):
    for series in data['series'].values():
        series['series'].pop('recurrence', None)
    assert find_problems(data) == []


def test_event_without_venue_ok(data):
    for _, _, event in _events(data):
        event.pop('venue', None)
    assert find_problems(data) == []


def test_series_without_events_directory_ok(data):
    # pyvocz uses data.get('events', {}) for a series
    slug = sorted(data['series'])[0]
    del data['series'][slug]['events']
    assert find_problems(data) == []


def test_series_directory_without_series_yaml_is_reported_not_crashed(data):
    slug = sorted(data['series'])[0]
    del data['series'][slug]['series']
    assert any('series.yaml' in p and slug in p for p in find_problems(data))


def test_recurrence_without_rrule_is_reported_not_crashed(data):
    slug = next(s for s, c in sorted(data['series'].items())
                if 'recurrence' in c['series'])
    del data['series'][slug]['series']['recurrence']['rrule']
    assert any('rrule' in p and slug in p for p in find_problems(data))


def test_non_string_rrule_is_reported_not_crashed(data):
    slug = next(s for s, c in sorted(data['series'].items())
                if 'recurrence' in c['series'])
    data['series'][slug]['series']['recurrence']['rrule'] = ['FREQ=DAILY']
    assert any('rrule' in p and slug in p for p in find_problems(data))


def test_event_without_city_is_reported_not_crashed(data):
    event = _first_event(data)
    del event['city']
    assert any('missing city' in p and event['_source'] in p
               for p in find_problems(data))
