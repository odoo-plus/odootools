from collections import defaultdict

from pip._internal.network.session import PipSession
from pip._internal.req.req_file import parse_requirements
from pip._internal.req.constructors import (
    install_req_from_parsed_requirement
)


class Requirement(object):
    def __init__(self):
        self.extras = set()
        self.specifiers = set()
        self.links = set()
        self.editable = False


def merge_requirements(files):
    requirements = defaultdict(lambda: Requirement())
    links = set()

    session = PipSession()

    for filename in files:
        filename_str = str(filename)
        f_requirements = parse_requirements(filename_str, session=session)
        for parsed_requirement in f_requirements:
            requirement = install_req_from_parsed_requirement(
                parsed_requirement
            )

            if requirement.markers and not requirement.markers.evaluate():
                continue

            if not requirement.name:
                links.add(requirement.link.url)
                continue

            name = requirement.req.name.lower()
            specifiers = requirement.req.specifier
            extras = requirement.req.extras
            requirements[name].extras |= set(extras)
            requirements[name].specifiers |= set(specifiers)
            if requirement.link:
                requirements[name].links |= {requirement.link.url}
            requirements[name].editable |= requirement.editable

    result = []
    for key, value in requirements.items():
        if value.links:
            result.append("%s" % value.links.pop())
        else:
            requirement_line = [key]

            if value.extras:
                extras = [str(extra) for extra in value.extras]
                extras.sort()
                requirement_line.append("[{}]".format(
                    ",".join(extras)
                ))

            if value.specifiers:
                specifiers = [str(spec) for spec in value.specifiers]
                specifiers.sort()
                requirement_line.append(",".join(specifiers))

            result.append(" ".join(requirement_line))

    for link in links:
        result.append(link)

    return result
