"""
Render Modules
==============

This module cover a series of function that can be used to render
the html description of the module based on static content and the
description string in the manifest.

This behaves in similar ways as how Odoo render the description
string for modules within Odoo.

You may want to render html description of the module when you need
to display the module description to Odoo users or potentially in a
web store.
"""
import lxml
import lxml.html

from docutils import nodes
from docutils.utils import Reporter
from docutils.core import publish_string
from docutils.transforms import Transform, writer_aux
from docutils.writers.html4css1 import Writer


class MyFilterMessages(Transform):
    """
    Custom docutils transform to remove `system message` for a document and
    generate warnings.

    (The standard filter removes them based on some `report_level` passed in
    the `settings_override` dictionary, but if we use it, we can't see them
    and generate warnings.)
    """
    default_priority = 870

    def apply(self):
        for node in self.document.traverse(nodes.system_message):
            node.parent.remove(node)


class MyWriter(Writer):
    """
    Custom docutils html4ccs1 writer that doesn't add the warnings to the
    output document.
    """
    def get_transforms(self):
        return [MyFilterMessages, writer_aux.Admonitions]


def render_description_str(path, description=''):
    html_file = path / "static/description/index.html"

    if html_file.exists():
        doc = html_file.open('rb').read()
        html = lxml.html.document_fromstring(doc)
        for element, attribute, link, pos in html.iterlinks():
            # TODO convert to an actual url that can work
            # especially if the assets aren't loaded anywhere exactly
            if (
                element.get('src') and
                '//' not in element.get('src') and
                'static/' not in element.get('src')
            ):
                element.set(
                    'src',
                    "/%s/static/description/%s" % (
                        path.name, element.get('src')
                    )
                )

        return lxml.html.tostring(html).decode()

    readme_files = ['README.rst', 'README.md', 'README.txt']

    for readme in readme_files:
        readme_path = path / readme

        if not readme_path.exists():
            continue

        readme_data = readme_path.open().read()
        break
    else:
        readme_data = description

    overrides = {
        'embed_stylesheet': False,
        'doctitle_xform': False,
        'output_encoding': 'unicode',
        'xml_declaration': False,
        'file_insertion_enabled': False,
        'report_level': Reporter.ERROR_LEVEL
    }

    description_html = publish_string(
        source=readme_data,
        settings_overrides=overrides,
        writer=MyWriter()
    )

    return description_html
