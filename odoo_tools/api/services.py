from zipfile import ZipFile
import giturlparse
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from ..configuration.git import fetch_addons, checkout_repo
from ..services.objects import ServiceManifests
from ..modules.search import find_modules_paths


_logger = logging.getLogger(__name__)


class ServiceApi(object):

    def __init__(self, env, cache=None):
        self.environment = env
        self.cache_path = cache

    def get_services(self, lookup_path):
        lookup_path = Path(lookup_path)

        if lookup_path.exists():
            services_path = lookup_path

        data = self.environment.loader.load_file(services_path)
        return ServiceManifests.parse(data)

    def checkout(
        self,
        service,
        target_path,
        fetch_path=None,
        decrypt_key=None
    ):
        if not fetch_path:
            fetch_path = target_path

        results = []

        for key, addon in service.addons.items():
            if not giturlparse.parse(addon.url).valid:
                _logger.info(
                    "Skipping addon %s as it has an invalid url.", addon.url
                )
                continue

            checkout_path = Path.cwd() / target_path / addon.repo_path

            path, info = fetch_addons(
                addon,
                fetch_path,
                decrypt_key=decrypt_key
            )

            if fetch_path != checkout_path:
                checkout_repo(path, checkout_path)

            results.append(info)

        return results

    def package(
        self,
        service,
        output_path,
        fetch_path=None,
        decrypt_key=None,
        temp_dir_manager=TemporaryDirectory
    ):
        with temp_dir_manager() as tempdir:
            target = Path(tempdir)

            self.checkout(
                service,
                target,
                fetch_path,
                decrypt_key
            )

            zipfile = ZipFile(str(output_path), 'w')

            # TODO copy modules and requirements.txt file and skip the rest
            for file in target.rglob("*"):
                if '.git' in file.parts:
                    continue

                if '.github' in file.parts:
                    continue

                if not file.is_file():
                    continue

                zip_filename = file.relative_to(target)

                with file.open('rb') as fin:
                    with zipfile.open(str(zip_filename), mode='w') as fout:
                        fout.write(fin.read())
