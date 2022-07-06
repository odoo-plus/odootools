from odoo_tools.modules.render import render_description_str
from six import ensure_text


readme_file_data = """
README_FILE
===========

Some Readme File
"""


def test_rendering(tmp_path):
    description = render_description_str(tmp_path, "Empty")

    assert "Empty" in description


def test_static_rendering(tmp_path):
    html_file = tmp_path / "static/description/index.html"

    html_file.parent.mkdir(parents=True, exist_ok=True)

    assert tmp_path.parent.exists() is True

    with html_file.open("w") as fin:
        fin.write(ensure_text("STATIC_HTML_FILE"))

    description = render_description_str(tmp_path, "Empty")

    assert "STATIC_HTML_FILE" in description
    assert "Empty" not in description


def test_render_readme(tmp_path):
    readme_file = tmp_path / "README.rst"

    tmp_path.parent.mkdir(parents=True, exist_ok=True)

    with readme_file.open("w") as fin:
        fin.write(ensure_text(readme_file_data))

    description = render_description_str(tmp_path, "Empty")

    assert "README_FILE" in description
