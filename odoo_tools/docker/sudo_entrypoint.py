import logging

from ..compat import pipe

_logger = logging.getLogger(__name__)


def install_apt_packages(odoo_env):
    """
    Install debian dependencies.
    """
    package_list = odoo_env.manage.packages()

    if len(package_list) > 0:
        _logger.info(
            "Installing %s",
            package_list
        )
        ret = pipe(['apt-get', 'update'])

        # Something went wrong, stop the service as it's failing
        if ret != 0:
            raise SystemError("Apt Update failed")

        base_install_params = ['apt-get', 'install', '-y']

        if not odoo_env.context.apt_install_recommends:
            base_install_params.append('--no-install-recommends')

        ret = pipe(
            base_install_params,
            list(package_list)
        )

        # Something went wrong, stop the service as it's failing
        if ret != 0:
            raise SystemError("Failed to install packages")


def fix_access_rights(odoo_env):
    # Change to some python alternative of chown/chmod
    # provide a way to configure user:group names
    if odoo_env.context.reset_access_rights == 'TRUE':
        pipe(["chown", "-R", "odoo:odoo", "/var/lib/odoo"])
        pipe(["chown", "-R", "odoo:odoo", "/etc/odoo"])


def remove_sudo():
    # TODO maybe add a file in sudoers.d and simply ensure it is removed
    return pipe(["sed", "-i", "/odoo/d", "/etc/sudoers"])
