import pytest
from mock import patch, MagicMock
from odoo_tools.app.mixins.routing import _generate_routing_rules


@pytest.fixture
def modules():
    return {
        'odoo': MagicMock(),
        'odoo.addons': MagicMock(),
        'odoo.addons.base': MagicMock(),
        'odoo.http': MagicMock()
    }


class MockController1(object):
    children_classes = {
        "base": []
    }


def legacy_route(routes=None, type="http", auth='none'):
    def wrap(func):
        route_info = {
            "type": type,
            "routes": routes if isinstance(routes, list) else [routes],
            "auth": auth
        }
        setattr(func, 'routing', route_info)
        return func
    return wrap


def route(routes=None, type="http", auth='none'):
    def wrap(func):
        route_info = {
            "type": type,
            "routes": routes if isinstance(routes, list) else [routes],
            "auth": auth
        }
        setattr(func, 'original_routing', route_info)
        return func
    return wrap


class Controller1(MockController1):
    __module__ = 'odoo.addons.base'

    @legacy_route(["/broken"])
    def legacy_route(self):
        pass

    @route(routes=[])
    def empty_route(self):
        pass

    def not_route(self):
        pass

    @route(routes='/func2')
    def func2(self):
        pass


class Controller2(MockController1):
    __module__ = 'odoo.addons.base'

    @route(routes='/func')
    def func(self):
        pass

    def func3(self):
        pass


class Controller3(Controller2):
    __module__ = 'odoo.addons.base'

    value = 1

    # ignored as not auth none
    @route(routes="/func3", auth="public")
    def func3(self):
        pass

    @route(routes='/func', type="json")
    def func(self):
        pass


MockController1.children_classes['base'] = [
    Controller1,
    Controller2,
    Controller3
]


class MockController2(object):
    pass


def test_gen_routing(modules):
    global route

    http = modules['odoo.http']

    http.Controller = MockController1
    http.route = route

    with patch.dict('sys.modules', modules):
        routes = _generate_routing_rules(
            ['base', None],
            nodb_only=True,
            converters=None
        )
        results = []
        for route in routes:
            results.append(route)

        assert len(results) == 4

    http.controllers_per_module = {
        "base": [
            ('', Controller1),
            ('', Controller2),
            ('', Controller3),
        ]
    }
    delattr(MockController1, 'children_classes')

    with patch.dict('sys.modules', modules):
        routes = _generate_routing_rules(
            ['base', None],
            nodb_only=True,
            converters=None
        )
        results = []
        for route in routes:
            results.append(route)

        assert len(results) == 4
