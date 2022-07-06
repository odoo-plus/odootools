from odoo_tools.utilities.requirements import merge_requirements


def test_merge_requirements(tmp_path):
    req1 = """cryptography
Pillow >3.0
invalid_module; python_version > '40.8'
"""
    req2 = """
gevent < 11
gevent > 2
Pillow <10
requests
requests[ssl] <3; python_version <= '4'
"""

    req3 = """git+https://github.com/path/to/package-two@41b95ec#egg=package-two
"""

    requirements = set()

    for index, req in enumerate([req1, req2, req3]):
        filename = tmp_path / f'requirements{index}.txt'
        with filename.open('w') as fout:
            fout.write(req)

        requirements.add(filename)

    result = merge_requirements(requirements)

    assert set(result) == set([
        'git+https://github.com/path/to/package-two@41b95ec#egg=package-two',
        'cryptography',
        'pillow <10,>3.0',
        'gevent <11,>2',
        'requests [ssl] <3'
    ])
