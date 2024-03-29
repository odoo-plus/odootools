import setuptools
from pathlib import Path

with open("README.md", "r") as fh:
    long_description = fh.read()


def find_in_path(module, path):
    def find_files(cur_path):
        files = []
        for path in cur_path.iterdir():
            if not path.is_dir():
                files.append(str(path))
            else:
                files += find_files(path)
        return files

    module_path = Path.cwd() / module / path

    return find_files(module_path)


setuptools.setup(
    name="odoo-tools",
    version="0.1.9",
    author="Loïc Faure-Lacroix <lamerstar@gmail.com>",
    author_email="lamerstar@gmail.com",
    description="Odoo Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://odoo-tools.readthedocs.io",
    project_urls={
        "Source": "https://github.com/llacroix/odoo-tools",
        "Documentation": "https://odoo-tools.readthedocs.io",
    },
    packages=setuptools.find_packages(),
    install_requires=[
        "giturlparse",
        "toposort",
        "toml",
        "requests",
        "packaging",
        "lxml",
        "docutils",
        "distro",
        "polib",
        "six>=1.12.0",
        "cryptography",
        "click",
        "passlib",
        "ptpython",
        "pip>=10.0",
        "password-strength",
        "psycopg2",
        "overlaymodule",
    ],
    extras_require={
        "docs": [
            "sphinx",
            "furo",
            "sphinx-argparse",
            "sphinx-click",
            "sphinxcontrib.asciinema",
        ],
        "test": [
            "mock",
            "pytest",
            "pytest-cov"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "odootools = odoo_tools.cli.odot:command",
        ],
        "odootools.registry": [
            "registry = odoo_tools.cli.registry:registry",
        ],
        "odootools.command": [
            "module = odoo_tools.cli.click.module:module",
            "addons_paths = odoo_tools.cli.click.path:addons_paths",
            "config = odoo_tools.cli.click.config:config",
            "entrypoint = odoo_tools.cli.click.entrypoint:entrypoint",
            "shell = odoo_tools.cli.click.shell:shell",
            "manage = odoo_tools.cli.click.manage:manage",
            "service = odoo_tools.cli.click.services:service",
            "platform = odoo_tools.cli.click.platform:platform",
            "user = odoo_tools.cli.click.users:user",
            "db = odoo_tools.cli.click.db:db",
            "gen = odoo_tools.cli.click.gen:gen",
        ]
    },
    package_data={
        "odoo_tools": (
            find_in_path('odoo_tools', 'requirements') +
            find_in_path('odoo_tools', 'overlays') +
            find_in_path('odoo_tools', 'packages')
        )
    }
)
