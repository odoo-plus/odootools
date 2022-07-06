import six
from six import ensure_binary, ensure_text
import shutil
import logging
from ast import literal_eval
import tempfile
from zipfile import ZipFile

from ..compat import Path
from ..modules.render import render_description_str
from ..modules.translate import PoFileWriter, PoFileReader
from ..exceptions import ArgumentError

_logger = logging.getLogger(__name__)


class CompanySpec(object):
    def __init__(self, country_code):
        self.country_code = country_code


def try_parse_manifest(data):
    return literal_eval(data)


def try_compile_manifest(data):
    code = compile(
        data,
        '__manifest__.py',
        'eval'
    )
    return eval(code, {}, {})


def get_translation_filename(language, module):
    """
    Get the filename for translation file.

    When no language is provided to translate a module,
    the name of the file will the name of the module as
    a pot file.

    For example, exporting the pot file for module bus would be
    exported by calling:

    ..code:: python

    get_translation_filename(None, 'bus')
    >> 'bus.pot'

    When exporting the translation file for fr_FR language for
    the module bus. It will return the family of the language
    as the langage and dialect are the same.

    ..code:: python

    get_translation_filename('fr_FR', 'bus')
    >> 'fr.po'

    If the language and dialect are different it returns the language
    locale as is.

    ..code:: python
    get_translation_filename('fr_CA', 'bus')
    >> 'fr_CA.po'

    Args:

        language (str|None): locale to export

        module (str): Name of the module to export

    Returns:

        str: The filename of the translation file based
            on the arguments.
    """
    if language and '_' in language:
        family, dialect = language.lower().split('_')
        if family == dialect:
            language = family

    filename = (
        '{}.po'.format(language)
        if language
        else '{}.pot'.format(module)
    )
    return filename


class Manifest(object):
    """
    Manifest Object

    The manifest object contains data stored in odoo/openerp manifests.
    """

    properties = {
        "_attrs",
        "path",
        "_manifest_file"
    }

    defaults = {
        "installable": True,
        "application": False,
        "depends": [],
        "demo": [],
        "data": [],
        "version": "0.0.0",
        "external_dependencies": dict
    }

    def __init__(self, path, attrs=None, manifest_file=None):
        """
        Initialize manifest objects. All attributes are stored into
        `_attrs`.
        """
        if attrs is None:
            attrs = {}

        self._attrs = attrs
        self.path = Path(path)

        if 'technical_name' not in attrs:
            attrs['technical_name'] = self.path.name

        self._manifest_file = manifest_file or (self.path / '__manifest__.py')

        self.set_defaults()

    def set_defaults(self):
        """
        Set some defaults when initializing an object
        """
        for key, value in Manifest.defaults.items():
            if key not in self._attrs:
                if callable(value):
                    self._attrs[key] = value()
                else:
                    self._attrs[key] = value

    def __getattr__(self, name, default=None):
        return self._attrs.get(name, default)

    def __setattr__(self, name, value):
        if (
            name in Manifest.properties
            # name in Manifest.defaults.keys()
        ):
            super(Manifest, self).__setattr__(name, value)
        else:
            self._attrs[name] = value

    def __lt__(self, other):
        return self.path.name < other.path.name

    def __eq__(self, other):
        if isinstance(other, Manifest):
            return self.path == other.path
        elif isinstance(other, str):
            return self.path.name == Path(other).name
        else:
            return False

    def __contains__(self, value):
        return value in self._attrs

    def __hash__(self):
        return hash(self.path.name)

    def __str__(self):
        return str(self.path)

    def __repr__(self):
        return "Manifest({path}, {attrs})".format(
            path=repr(self.path),
            attrs=repr(self._attrs)
        )

    def values(self):
        """
        Return manifest values
        """
        return self._attrs

    def set_attribute(self, attribute, value):
        if len(attribute) == 0:
            raise ArgumentError(
                'The attribute must have at least one attribute name.'
            )
        cur_vals = self._attrs

        last_attribute = attribute[-1]

        for attr in attribute[:-1]:
            if attr not in cur_vals:
                cur_vals[attr] = {}
            cur_vals = cur_vals[attr]
        else:
            cur_vals[last_attribute] = value

    def static_assets(self):
        addons_path = self.path.parent

        def recurse_search(cur_dir):
            files = []
            for file in cur_dir.iterdir():
                if file.is_dir():
                    files += recurse_search(file)
                else:
                    static_path = file.relative_to(addons_path)
                    files.append((static_path, file))
            return files

        if (self.path / "static").exists():
            return recurse_search(self.path / "static")
        else:
            return []

    @classmethod
    def from_path(klass, manifest, render_description=False):
        """
        Loads the manifest from a given path.

        It automatically define the module name to the path name of the
        folder in which the manifest is located to those attributes:

        - name
        - technical_name

        A custom attribute `description_html` can be generated to store
        the rendered html description.

        Args:
            manifest (Path): The path of the manifest or module.
            render_description (bool): Set to True if you need to render
              the description.

        Returns:
            Manifest: The manifest that was loaded.
        """
        if not manifest.name.endswith('py'):
            module_path = manifest
            odoo_manifest = module_path / '__manifest__.py'
            erp_manifest = module_path / '__openerp__.py'

            manifest = None
            if odoo_manifest.exists():
                manifest = odoo_manifest
            if not manifest and erp_manifest.exists():
                manifest = erp_manifest
        else:
            module_path = manifest.parent

        with manifest.open('rb') as fin:
            manifest_data = ensure_text(fin.read() or "")
            manifest_data = manifest_data.replace('\ufeff', '')

        parsers = [
            try_parse_manifest,
            try_compile_manifest,
            # try_parse_manifest_encoded,
            # try_compile_manifest_encoded
        ]

        last_error = None
        for parser in parsers:
            try:
                data = parser(manifest_data)
                break
            except Exception as exc:
                last_error = exc
        else:
            data = {}
            if last_error is not None:
                _logger.error(
                    "Cannot parse manifest: {}".format(
                        manifest,
                    ),
                )
                raise last_error

        if 'name' not in data:
            data['name'] = module_path.name

        data['technical_name'] = module_path.name

        if render_description:
            data['description_html'] = render_description_str(
                module_path,
                data.get('description', '')
            )

        man = Manifest(module_path, attrs=data, manifest_file=manifest)

        return man

    def save(self):
        obj = {}
        for key, value in self._attrs.items():
            if key in ['description_html', 'technical_name']:
                continue

            if isinstance(value, Path):
                obj[key] = str(value)
            else:
                obj[key] = value

        if not self._manifest_file.parent.exists():
            self._manifest_file.parent.mkdir(parents=True)

        with self._manifest_file.open('w') as fout:
            fout.write(repr(obj))

    def requirements(self, package_map=None):
        """
        Return a list of packages required by module.
        """
        packages = set()

        for package in self.external_dependencies.get('python', []):
            package_lower = package.lower()

            if package_map and package_lower in package_map:
                package_name = package_map[package.lower()]
                if package_name:
                    packages.add(package_name)
            else:
                packages.add(package)

        return packages

    def disable(self):
        self.installable = False

    def remove(self):
        """
        Remove the module from the file system
        """
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def files(self):
        for file in self.path.glob('**/*'):
            if file.is_dir():
                continue
            if file.name.endswith('.pyc'):
                continue

            yield file

    def package(self):
        outfile = tempfile.NamedTemporaryFile()

        root_folder = self.path.parent
        zipfile = ZipFile(outfile, 'w')

        for file in self.files():
            zip_filename = file.relative_to(root_folder)

            with file.open('rb') as fin:
                with zipfile.open(str(zip_filename), mode='w') as fout:
                    fout.write(fin.read())

        return outfile

    def export_translations(self, db, languages):

        translations = db.export_translation_terms(
            languages,
            [self.technical_name]
        )

        for language, module, rows in translations:
            filename = get_translation_filename(language, module)
            trans_path = self.path / 'i18n' / filename
            trans_path.parent.mkdir(parents=True, exist_ok=True)

            _logger.info(
                "Exporting translation %s of module %s to %s",
                language,
                module,
                trans_path
            )

            if trans_path.exists():
                origin_po_file = PoFileReader(trans_path.open('rb'))
            else:
                with trans_path.open("w+") as buffer:
                    buffer.write("")

                with trans_path.open('rb') as buffer:
                    origin_po_file = PoFileReader(buffer)

            with trans_path.open('wb+') as buffer:
                po_writer = PoFileWriter(
                    buffer,
                    language,
                    pofile=origin_po_file.pofile
                )

                po_writer.add_entries(rows)

                po_writer.write()
