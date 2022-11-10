import sys
from odoo_tools.compat import Path
from ..configuration.git import checkout_repo
from .misc import (
    run,
    cd,
    get_resource
)
from tempfile import TemporaryDirectory
from six import ensure_binary, ensure_str
import logging
import requests
from packaging.version import parse as version_parse
from .pip import pip_command

_logger = logging.getLogger(__name__)


requirement_file_template = "requirements/requirements-{version}.0.txt"


class OdooSource(object):
    def __init__(self, version, options=None, cache=None):
        self.version = version
        self.cache = cache
        self.options = options
        self.target = None

    def __enter__(self):
        self.target = TemporaryDirectory()
        self.target_path = Path(self.target.name)

        if not self.cache:
            self.cache = self.target_path / 'cache'
            self.cache.mkdir(parents=True, exist_ok=True)

        return self

    def __exit__(self, *args, **kwargs):
        pass

    @property
    def parsed_version(self):
        return version_parse(self.version)

    @property
    def requirement_file(self):
        resource_file = requirement_file_template.format(
            version=self.parsed_version.major
        )
        resource_path = get_resource('odoo_tools', resource_file)
        if not resource_path.exists():
            resource_path = self.odoo_dir / 'requirements.txt'

        return resource_path

    def setup_installed_release(self, version, installed_release):
        _logger.info("Patching odoo/release.py with installed release")

        if version.major > 9:
            release_py = 'odoo/release.py'
        else:
            release_py = 'openerp/release.py'

        release_file = self.odoo_dir / release_py

        with release_file.open('r') as release_fd:
            release_code = release_fd.read()

        with release_file.open('wb') as release_fd:
            release_fd.write(ensure_binary(release_code))
            release_fd.write(ensure_binary("\n"))
            release_fd.write(ensure_binary(
                "installed_release = {}".format(installed_release)
            ))

    def strip_languages(self, languages):
        if not languages or languages == 'all':
            return

        prefix = set()

        for lang in languages.split(','):
            if not lang:
                continue

            lang_parts = lang.split('_')
            if len(lang_parts) == 2:
                prefix.add(lang_parts[0])
            prefix.add(lang)

        for file in self.odoo_dir.rglob('*.po'):
            filename = file.name[:-3]
            if filename not in prefix:
                try:
                    file.unlink()
                except Exception:
                    pass

    def fetch(self):
        raise NotImplementedError()

    def checkout(self):
        raise NotImplementedError()

    def need_update(self):
        try:
            import odoo
            release = odoo.release.installed_release
            if release == self.installed_release:
                _logger.info("Odoo is already up to date")
                return False
        except Exception:
            pass

        return True

    def install(self):
        self.setup_installed_release(
            self.parsed_version,
            self.installed_release
        )

        languages = self.options.languages

        self.strip_languages(languages)

        _logger.info("Installing odoo")

        target = self.options.target
        upgrade = self.options.upgrade

        args = pip_command(target=target, upgrade=upgrade)

        # Ensure setuptools less than 58 is installed for odoo
        # versions from 11 to 13.
        if (
            self.parsed_version.major > 10 and
            self.parsed_version.major < 14
        ):
            new_args = args[:]
            new_args += [
                "setuptools<58"
            ]

            run(new_args)

        args += ['.', '-r', str(self.requirement_file)]

        with cd(self.odoo_dir):
            _logger.info("Installing odoo with command: '%s'", " ".join(args))
            run(args)


class GitRelease(OdooSource):
    def __init__(self, version, repo, ref, options=None, cache=None):
        super().__init__(version, options=options, cache=cache)
        self.repo = repo
        self.ref = ref

    @property
    def installed_release(self):
        return {
            "source": self.repo,
            "release": ensure_str(self.commit_id).replace('\n', ''),
        }

    def fetch(self):
        self.cached_odoo_dir = self.cache / 'odoo'
        self.cached_odoo_dir.mkdir(exist_ok=True, parents=True)

        with cd(self.cached_odoo_dir):
            head_file = self.cached_odoo_dir / 'HEAD'
            if not head_file.exists():
                run(['git', 'init', '--bare'])
                _logger.info("Fetching Odoo %:%", self.repo, self.ref)
                run(['git', 'fetch', '--depth', '1', self.repo, self.ref])
            else:
                run(['git', 'fetch', self.repo, self.ref])

    def checkout(self):
        self.odoo_dir = self.target_path / 'odoo'
        self.odoo_dir.mkdir(exist_ok=True, parents=True)

        self.commit_id = checkout_repo(self.cached_odoo_dir, self.odoo_dir)

    def install(self):
        target_addons_path = (
            'odoo/addons'
            if self.parsed_version.major > 9
            else 'openerp/addons'
        )

        target_path = self.odoo_dir / target_addons_path
        # Copy addons in /addons and add into odoo/addons to be installed
        # with the package
        _logger.info("Moving addons into package")
        for addons in (self.odoo_dir / 'addons').iterdir():
            run(['mv', str(addons), str(target_path)])

        super().install()


class OfficialRelease(OdooSource):

    def __init__(self, version, release, options=None, cache=None):
        super().__init__(version, options=options, cache=cache)
        self.release = release
        self.base_domain = "https://nightly.odoo.com"

    def fetch(self):

        path_fmt = "{version}/nightly/src"

        if '/' in self.release:
            release_path, release = self.release.split('/', 1)
            path = path_fmt.format(
                version=release_path
            )
        else:
            path = path_fmt.format(
                version=self.version
            )

        filename = "odoo_{version}.{release}.tar.gz".format(
            version=self.version,
            release=self.release
        )

        url = "{base_domain}/{path}/{filename}".format(
            base_domain=self.base_domain,
            path=path,
            filename=filename
        )

        output_file = self.cache / filename

        self.output_file = output_file

        if output_file.exists():
            _logger.info("Skipping fetch %s as file is already cached", url)
            return

        data_size = 0

        with requests.get(url, stream=True) as req:
            req.raise_for_status()

            with output_file.open('wb') as fout:
                for chunk in req.iter_content(chunk_size=8192):
                    data_size += len(chunk)
                    fout.write(chunk)

        _logger.info("Wrote % bytes to disk", data_size)

    def checkout(self):
        _logger.info("Extracting archive")
        output_dir = self.target_path / "odoo"
        output_dir.mkdir()
        run(['tar', '-xzf', str(self.output_file), '-C', str(output_dir)])
        self.odoo_dir = next(output_dir.iterdir())

    @property
    def installed_release(self):
        return {
            "source": self.base_domain,
            "release": self.release,
            "version": self.version
        }

    def install(self):
        super().install()
