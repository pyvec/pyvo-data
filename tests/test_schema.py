from pathlib import Path
import datetime

import jsonschema
import yaml

from pyvodb.load import dict_from_directory

data_dir = Path(__file__).parent.parent

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


def test_schema():
    """Test that all data conforms to the schema"""
    with (data_dir / 'meta.yaml').open() as f:
        metadata = yaml.safe_load(f)
    data = dict_from_directory('.', data_dir,
                               ignored_files=metadata['ignored_files'])

    # Since we load all YAML files, the schema is part of the data itself
    schema = data['schema']

    validator = jsonschema.validators.validator_for(schema)
    validator = jsonschema.validators.extend(
        validator,
        {'const': validate_const, 'enum': validate_enum})

    jsonschema.validate(data, schema,
                        cls=validator,
                        format_checker=format_checker)

if __name__ == '__main__':
    test_schema()
