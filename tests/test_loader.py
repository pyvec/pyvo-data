import pytest

from loader import dict_from_directory


def test_yaml_files_get_source_and_key(tmp_path):
    (tmp_path / 'a.yaml').write_text('x: 1\n')
    data = dict_from_directory('.', tmp_path)
    assert data == {'a': {'x': 1, '_source': 'a.yaml'}}


def test_nested_directories_become_nested_dicts(tmp_path):
    (tmp_path / 'd').mkdir()
    (tmp_path / 'd' / 'b.yaml').write_text('y: 2\n')
    data = dict_from_directory('.', tmp_path)
    assert data == {'d': {'b': {'y': 2, '_source': 'd/b.yaml'}}}


def test_ignored_names_and_dotfiles_skipped_at_top_level(tmp_path):
    (tmp_path / 'README.md').write_text('hi')
    (tmp_path / '.git').mkdir()
    (tmp_path / '.git' / 'HEAD').write_text('ref')
    (tmp_path / 'a.yaml').write_text('x: 1\n')
    data = dict_from_directory('.', tmp_path, ignored_files=['README.md'])
    assert list(data) == ['a']


def test_unexpected_file_raises(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'notes.txt').write_text('hi')
    with pytest.raises(ValueError, match='Unexpected file'):
        dict_from_directory('.', tmp_path)


def test_ignored_name_nested_in_subdirectory_still_raises(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'README.md').write_text('hi')
    with pytest.raises(ValueError, match='Unexpected file'):
        dict_from_directory('.', tmp_path, ignored_files=['README.md'])


@pytest.mark.parametrize('content', ['', '# only a comment\n', '- a\n- list\n'])
def test_yaml_file_that_is_not_a_mapping_names_the_file(tmp_path, content):
    (tmp_path / 'd').mkdir()
    (tmp_path / 'd' / 'bad.yaml').write_text(content)
    with pytest.raises(ValueError, match=r'd/bad\.yaml.*mapping'):
        dict_from_directory('.', tmp_path)
