import hashlib
from six import ensure_text
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
    """
    This class represent a company object.

    This object can be used along database initialization.
    When creating a new database, it is possible to configure the
    main company before installing more modules. One example where
    the company is particularly important is when you attempt to
    install the account module.

    Without a valid company, Odoo will try to install a default
    l10n module for accounting for a locale that you would likely
    not use.

    When a company object is provided to the database initialization,
    it will start by initializing the database with the base module.

    Then when the base module is installed, it will update some objects
    like the `res.company` and then it will install other modules that
    were requested to be installed for the database initialization.

    Attributes:
        country_code (str): Country code based on the Alpha-2 of the
            `ISO 3166-1 <ISO>`_ code.
    .. _ISO: https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes
    """
    def __init__(self, country_code):
        self.country_code = country_code


def try_parse_manifest(data):
    """
    Attempt parsing a manifest.

    It used the literal_eval native function to attempt parsing
    a manifest.

    Args:
        data (str): Content of the manifest to load

    Returns:
        dict: The parsed data of the manifest.
    """
    return literal_eval(data)


def try_compile_manifest(data):
    """
    Attempt compiling the manifest.

    In some specific cases, if the literal eval doesn't work. It can
    provide more information to compile the manifest and evaluate its
    content.

    As manifest file are python modules, it is technically possible
    to import or use python code directly within the manifest file.

    In that case a simple literal_eval wouldn't be enough. That said,
    this evaluator should never be used.

    Args:
        data (str): Content of the manifest to load

    Returns:
        dict: The parsed data of the manifest.
    """
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

    .. code-block:: python

        get_translation_filename(None, 'bus')
        >> 'bus.pot'

    When exporting the translation file for fr_FR language for
    the module bus. It will return the family of the language
    as the langage and dialect are the same.

    .. code-block:: python

        get_translation_filename('fr_FR', 'bus')
        >> 'fr.po'

    If the language and dialect are different it returns the language
    locale as is.

    .. code-block:: python

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

    Attributes:
        _attrs (dict): Data of the manifest file. You can see the whole set
            of attributes in the `odoo documentation <odoo>`_.

        path (Path): The path in which the manifest got loaded.

        _manifest_file: The path of the manifest file of this manifest
            if it was loaded from a path. If the path of the manifest
            wasn't provided, it defaults to the filename `__manifest__.py`
            in the path of the module.

        technical_name: This attribute is stored into the _attrs but is defined
            as the module name. The name attribute in a manifest is just a name
            that will then get loaded in odoo. The technical name is the unique
            identifier for the module path in the addons paths.

    .. _odoo: https://www.odoo.com/documentation/master/developer/reference/backend/module.html
    """  # noqa

    properties = {
        "_attrs",
        "path",
        "_manifest_file"
    }

    defaults = {
        "installable": True,
        "application": False,
        "depends": list,
        "demo": list,
        "data": list,
        "version": "0.0.0",
        "external_dependencies": dict
    }

    def __init__(self, path, attrs=None, manifest_file=None):
        """
        Initialize manifest objects.

        Args:
            path (Path): Path in which the module is located

            attrs (dict): Data to set in the manifest.

            manifest_file (Path): Location of the manifest itself if provided.
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
        Set some defaults when initializing an object.

        It uses the values as defined in `Manifest.defaults`. If a value
        is already present in `self._attrs`, it will not update the value
        from the defaults.
        """
        for key, value in Manifest.defaults.items():
            if key not in self._attrs:
                if callable(value):
                    self._attrs[key] = value()
                else:
                    self._attrs[key] = value

    def __getattr__(self, name, default=None):
        """
        Get an attribute from `self._attrs`.
        """
        return self._attrs.get(name, default)

    def __setattr__(self, name, value):
        """
        Set an attribute into the manifest. If it is a protected
        attribute, it will use the super method, otherwise it will
        set the custom attributes in `self._attrs`.

        The reason why some attributes are separate is that you
        wouldn't want to save some attributes to the manifest. For
        example, the `path` of the module doesn't have to get saved.
        """
        if (
            name in Manifest.properties
            # name in Manifest.defaults.keys()
        ):
            super(Manifest, self).__setattr__(name, value)
        else:
            self._attrs[name] = value

    def __lt__(self, other):
        """
        Comparison function using the name property.

        It is required to make Manifest sortable in a list by name.
        Sorting modules lists can be required in order to give
        consistent results.

        For example, a simple text diff would fail if the module set
        was returned in random order. When sorting the modules in a list,
        the output will always be the same if both sets are the same.

        Args:
            other (Manifest): The other manifest to be compared against.

        Returns:
            bool: if the name is bigger than the other name.
        """
        return self.path.name < other.path.name

    def __eq__(self, other):
        """
        Compare a manifest against something else.

        This method will compare an other object with the path name of
        the current manifest. The other will be converted to a path name
        if possible and compared. If it's not possible to compare it to
        a path name, then it is considered as unequal.

        Args:
            other (Manifest|str|Path,Any): the other to be checked against.
        """
        if isinstance(other, Manifest):
            return self.path == other.path
        elif isinstance(other, str):
            return self.path.name == Path(other).name
        elif isinstance(other, Path):
            return self.path.name == other.name
        else:
            return False

    def __contains__(self, value):
        """
        Check if a property is defined in properties of the
        manifest.

        Example:

        .. code-block: python

            'technical_name' in self
            >> True

        Args:
            value (str): Name of a property

        Returns:
            bool: If the property is present in the manifest.
        """
        return value in self._attrs

    def __hash__(self):
        """
        Makes the manifest hashable based on its name.

        In practice two modules in different path would get
        the same hash. The reason for this is that odoo doesn't
        handle having 2 different modules with the same path name.

        When importing a module it could pick one or the other module
        based on how `odoo.addons` searches for modules within the
        defined paths.

        Obviously, you should check if you have 2 modules with the
        same technical name.
        """
        return hash(self.path.name)

    def __str__(self):
        """
        Serialize the str interpretation of a manifest.
        """
        return str(self.path)

    def __repr__(self):
        """
        Python representation of a manifest with all its properties.
        """
        return "Manifest({path}, {attrs})".format(
            path=repr(self.path),
            attrs=repr(self._attrs)
        )

    def values(self):
        """
        Returns the manifest's properties.
        """
        return self._attrs

    def set_attribute(self, attribute, value):
        """
        Set attribute to a value.

        This is a shortcut method to set attributes in a nested dict.

        .. code-block:: python

            manifest.set_attribute(
                ['external_dependencies', 'python'], ['request']
            )
            assert manifest.external_dependencies['python'] == ['request']

        Args:
            attribute (list(str)): List of attribute key to set

            value (any): Value to set to the attribute path
        """
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
        """
        Returns static asset files.

        This lookup all files in the static folder of the current
        module/manifest. It will return all files without exceptions.

        This can be mainly used to lookup for static assets of specific
        modules. For example, you'd want to upload all static assets
        somewhere else or you'd want to preprocess static assets before
        deployment.

        Returns:

            list(Path): A list of files static subdirectory
        """
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
        """
        Saves changes made to the manifest in python.

        All changes will be dumped into the original manifest
        file or in __manifest__.py.
        """
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
        """
        Set the manifest as uninstallable.
        """
        self.installable = False

    def remove(self):
        """
        Remove the module from the file system.

        It will attempt to remove the folder in which the
        manifest is located.

        If the directory doesn't exist, it does nothing.
        If the directory does exist. It will try to remove
        all files located in the module folder recursively.
        """
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def checksum(self):
        """
        Computes the checksum of the module itself.
        This can later be used to check if the module has changed
        and force an update of the module as the version that
        is installed doesn't match the one on the filesystem.
        """
        check = hashlib.sha1()

        for file in self.files():
            check.update(file.open('rb').read())

        return check

    def files(self):
        """
        Yields all file located in the module's folder.

        Iterating over this iterator yields all file in the module's
        folder except pyc files or potentially other files that aren't
        considered as "sources". It will also yield files located in
        the static folder.
        """
        all_files = [
            file
            for file in self.path.glob('**/*')
            if not file.is_dir()
            if not file.name.endswith('.pyc')
        ]

        all_files.sort()

        for file in all_files:
            yield file

    def package(self):
        """
        Returns a file handle to a zipfile of the packaged module.

        This methods will generate a zip file based on the result of
        a call to `self.files()`.

        The zipfile will get destroyed once it is closed or garbage
        collected.

        Returns:
            File: A file handle containing the zipped module.
        """
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
        """
        Exports translation in the corresponding module's path.

        It will store all potential translations into the i18n folder
        of the corresponding module.

        Args:
            db (DbApi): the api used to access the database.

            languages (list(str)): list of locales to export.

        Returns:
            Nothing
        """

        translations = db.export_translation_terms(
            languages,
            [self.technical_name]
        )

        po_files = []

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

                po_files.append(po_writer)

        return po_files
