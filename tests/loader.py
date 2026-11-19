"""Load the data directory into a dict, as the pyvo consumers do."""
import os
from pathlib import Path

import yaml

# The C loader is several times faster; fall back if libyaml is unavailable
YAML_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def dict_from_directory(directory, root, ignored_files=()):
    """Return the YAML files under root/directory as a nested dict.

    Names in `ignored_files` (top level only) and dotfiles are skipped.
    Each `*.yaml` file becomes an entry keyed by its name without the
    extension, with `_source` set to its path relative to `root`.
    Any other non-directory file raises ValueError.
    """
    data = {}
    for filename in sorted(os.listdir(os.path.join(root, directory))):
        fullname = os.path.normpath(os.path.join(directory, filename))
        absname = os.path.join(root, fullname)
        if filename in ignored_files or filename.startswith('.'):
            continue
        if filename.endswith('.yaml'):
            with open(absname) as f:
                info = yaml.load(f, Loader=YAML_LOADER)
            if not isinstance(info, dict):
                raise ValueError(
                    f'{fullname}: expected a YAML mapping, '
                    f'got {type(info).__name__}')
            info['_source'] = fullname
            data[filename[:-len('.yaml')]] = info
        elif os.path.isdir(absname):
            data[filename] = dict_from_directory(fullname, root)
        else:
            raise ValueError('Unexpected file: ' + fullname)
    return data


DATA_DIR = Path(__file__).resolve().parent.parent


def load_data():
    """Load the whole repository the way the consumers do (see meta.yaml)"""
    with (DATA_DIR / 'meta.yaml').open() as f:
        metadata = yaml.load(f, Loader=YAML_LOADER)
    return dict_from_directory(
        '.', DATA_DIR, ignored_files=metadata['ignored_files'])
