import datetime

import jsonschema
import pytest

# Python jsonschema implements Draft 4 specification, but we want something
# extra from the current draft: "const" and "enum"

def validate_const(validator, value, instance, schema):
    if value != instance:
        yield jsonschema.exceptions.ValidationError(
            f'value is not {value}')


def validate_enum(validator, value, instance, schema):
    if instance not in value:
        yield jsonschema.exceptions.ValidationError(
            f'value is not one of {value}')

# Also, YAML parses dates & datetimes into Python objects.
# We add format validators for those

def assert_is_date(value):
    """Ensure value is a date object (but not datetime)"""
    if isinstance(value, datetime.datetime):
        raise TypeError(f'{value} is a datetime, not date')
    if not isinstance(value, datetime.date):
        raise TypeError(f'{value} is not datetime')
    return True

def assert_is_datetime(value):
    """Ensure value is a datetime object"""
    if not isinstance(value, datetime.datetime):
        raise TypeError(f'{value} is not a datetime')
    return True

format_checker = jsonschema.FormatChecker()
format_checker.checkers['date-time'] = (assert_is_datetime, TypeError)
format_checker.checkers['date'] = (assert_is_date, TypeError)


def validate(data):
    """Validate loaded data against the schema, raising ValidationError"""
    # Since we load all YAML files, the schema is part of the data itself
    schema = data['schema']

    validator = jsonschema.validators.validator_for(schema)
    validator = jsonschema.validators.extend(
        validator,
        {'const': validate_const, 'enum': validate_enum})

    jsonschema.validate(data, schema,
                        cls=validator,
                        format_checker=format_checker)


def test_schema(loaded_data):
    """Test that all data conforms to the schema"""
    validate(loaded_data)


def _first_series(data):
    slug = sorted(data['series'])[0]
    return data['series'][slug]


def assert_rejected(data, message, path_element):
    """The schema rejects `data` for the expected reason, not just any reason"""
    with pytest.raises(jsonschema.ValidationError) as excinfo:
        validate(data)
    error = excinfo.value
    assert message in error.message
    assert path_element in list(error.absolute_path)


@pytest.mark.parametrize('key', ['organizer-info', 'description'])
def test_series_requires(key, data):
    del _first_series(data)['series'][key]
    assert_rejected(data, f"'{key}' is a required property", 'series')


@pytest.mark.parametrize('start', [
    datetime.date(2020, 1, 2),
    datetime.datetime(2020, 1, 2, 18, 30),
])
def test_start_accepts_date_and_datetime(start, data):
    events = _first_series(data)['events']
    events[sorted(events)[0]]['start'] = start
    validate(data)


def _first_city(data):
    return data['cities'][sorted(data['cities'])[0]]


def _first_venue(data):
    for slug in sorted(data['cities']):
        venues = data['cities'][slug].get('venues')
        if venues:
            return venues[sorted(venues)[0]]
    raise LookupError('no venues')


def _first_event(data):
    events = _first_series(data)['events']
    return events[sorted(events)[0]]


# Each mutation removes something pyvocz reads unconditionally at load time
# (pyvocz/data.py), so data like that must fail here rather than in pyvocz.
# Value: (mutation, part of the expected error message, element of its path)
BREAKAGES = {
    'event-without-start': (
        lambda d: _first_event(d).pop('start'),
        "'start' is a required property", 'events'),
    # pyvocz does datetime.combine(start, ...), which crashes on a string
    'event-start-string': (
        lambda d: _first_event(d).update(start='2020-01-02 18:30'),
        'is not valid under any of the given schemas', 'start'),
    'city-without-name': (
        lambda d: _first_city(d)['city'].pop('name'),
        "'name' is a required property", 'city'),
    'city-without-location': (
        lambda d: _first_city(d)['city'].pop('location'),
        "'location' is a required property", 'city'),
    'city-location-empty': (
        lambda d: _first_city(d)['city'].update(location={}),
        "'latitude' is a required property", 'location'),
    'venue-location-without-longitude': (
        lambda d: _first_venue(d)['location'].pop('longitude'),
        "'longitude' is a required property", 'venues'),
    'series-dir-without-series-yaml': (
        lambda d: _first_series(d).pop('series'),
        "'series' is a required property", 'series'),
}


@pytest.mark.parametrize('name', sorted(BREAKAGES))
def test_schema_rejects_what_pyvocz_cannot_load(name, data):
    mutate, message, path_element = BREAKAGES[name]
    mutate(data)
    assert_rejected(data, message, path_element)
