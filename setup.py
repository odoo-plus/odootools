import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="odoo-tools",
    version="0.1.0",
    author="Loïc Faure-Lacroix <lamerstar@gmail.com>",
    author_email="lamerstar@gmail.com",
    description="Odoo Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/llacroix/odoo-utils.git",
    packages=setuptools.find_packages(),
    install_requires=[
        "giturlparse",
        "toposort",
        "toml",
        "requests",
        "pathlib2; python_version < '3.0'",
        "packaging",
        "lxml",
        "docutils",
        "polib",
        "six>=1.12.0",
        "cryptography",
        "click",
        "passlib",
        "ptpython",
    ],
    extras_require={
        "docs": [
            "sphinx",
            "furo",
            "sphinx-argparse",
            "sphinx-click",
        ],
        "test": [
            "mock",
            "pytest",
            "pytest-cov"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "odootools = odoo_tools.cli.odot:command"
        ],
    },
    package_data={
        "odoo_tools": [
            "requirements/*.txt",
            "packages/*.toml",
        ],
    }
)
