"""Package validated public source files into a QGIS installation ZIP."""
import ast
import configparser
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile


def build(output):
    root = Path(__file__).resolve().parent
    package = root / 'quick_field_keys'
    metadata = configparser.ConfigParser(interpolation=None)
    metadata.read(package / 'metadata.txt', encoding='utf-8')
    general = metadata['general']
    for key in ('name', 'description', 'version', 'qgisMinimumVersion',
                'qgisMaximumVersion', 'author', 'email', 'homepage', 'repository',
                'tracker', 'license', 'icon', 'changelog'):
        if not general.get(key, '').strip():
            raise ValueError(f'Missing required metadata: {key}')
    for key in ('homepage', 'repository', 'tracker'):
        if not general[key].startswith('https://github.com/HaYanJongSeong/qgis-quick-field-keys'):
            raise ValueError(f'Invalid public URL: {key}')
    assert general['license'] == 'GPL-3.0-or-later'
    files = {f'quick_field_keys/{name}': package / name
             for name in ('__init__.py', 'plugin.py', 'metadata.txt', 'icon.svg')}
    files.update({f'quick_field_keys/{name}': root / name
                  for name in ('README.md', 'LICENSE', 'CHANGELOG.md')})
    for archive_name, source in files.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.suffix == '.py':
            ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
        if '__pycache__' in archive_name or source.suffix == '.zip':
            raise ValueError('Generated files must not be included in the release.')
    license_text = (root / 'LICENSE').read_text(encoding='utf-8')
    assert 'GNU GENERAL PUBLIC LICENSE' in license_text
    assert 'Version 3, 29 June 2007' in license_text
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'quick_field_keys_{general["version"]}.zip'
    # Never overwrite an existing release archive.
    with ZipFile(archive, 'x', ZIP_DEFLATED) as zipped:
        for archive_name, source in files.items():
            zipped.write(source, archive_name)
    with ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert set(zipped.namelist()) == set(files)
        assert zipped.read('quick_field_keys/plugin.py') == (package / 'plugin.py').read_bytes()
    assert archive.stat().st_size < 25 * 1024 * 1024
    print(archive)
    return archive


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python build_release.py <output-directory>')
    build(sys.argv[1])
