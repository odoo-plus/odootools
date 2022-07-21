import warnings

try:
    from coverage.exceptions import CoverageWarning
except ImportError:
    CoverageWarning = None


def ignore_odoo_warnings():
    warnings.filterwarnings(
        'ignore',
        r'^Sampling from a set',
        category=DeprecationWarning,
        module='odoo'
    )

    warnings.filterwarnings(
        'ignore',
        r'^Using or importing the ABCs from',
        category=DeprecationWarning,
        module='jinja2'
    )


def ignore_default_warnings():
    if CoverageWarning:
        warnings.filterwarnings(
            'ignore',
            category=CoverageWarning,
            module='coverage',
        )

    warnings.filterwarnings(
        'ignore',
        r'nodes.Node.traverse()',
        category=PendingDeprecationWarning,
        module='docutils'
    )

    warnings.filterwarnings(
        'ignore',
        r'^Creating a LegacyVersion has been',
        category=DeprecationWarning,
        module='pip'
    )
