from .models import ParentedObject


class BaseField(property):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        if 'default' in kwargs:
            self._default = kwargs['default']

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, owner, klass):
        # When trying to get the property from a class
        if not owner:
            return self

        if self.name not in owner._data and hasattr(self, '_default'):
            return self._default
        else:
            return owner._data.get(self.name)

    def __set__(self, owner, value):
        owner._data[self.name] = self.parse(owner, value)

    def parse(self, owner, data):
        return data


class String(BaseField):
    _default = ""

    def parse(self, owner, data):
        return str(data)


class Boolean(BaseField):
    _default = False

    # def __init__(self, *args, **kwargs):
    #    if 'default' not in kwargs:
    #        kwargs['default'] = False
    #    super().__init__(*args, **kwargs)

    def parse(self, owner, data):
        return bool(data)


class Object(BaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_class = kwargs['object_class']

    def parse_object(self, owner, data):
        if not data:
            data = {}

        obj = self.object_class.parse(data)

        if isinstance(obj, ParentedObject):
            obj.set_parent(owner)

        return obj

    def parse(self, owner, data):
        return self.parse_object(owner, data)


class ProxyObject(BaseField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.getter = kwargs['getter']

    def parse(self, owner, data):
        return {
            "ref": data
        }

    def __get__(self, owner, klass):
        ref = super().__get__(owner, klass)
        if not ref:
            return None
        return getattr(owner, self.getter)(ref['ref'])


class List(Object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, owner, data):
        if not data:
            return []

        vals = [
            (
                item
                if isinstance(item, self.object_class)
                else self.parse_object(owner, item)
            )
            for item in data
        ]

        for val in vals:
            if isinstance(val, ParentedObject):
                val.set_parent(owner)

        return vals


class Dict(List):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._key = kwargs['key']

    def parse(self, owner, data):
        if isinstance(data, dict):

            for val in data.values():
                if isinstance(val, ParentedObject):
                    val.set_parent(owner)

            return data

        objects = super().parse(owner, data)

        return {
            getattr(item, self._key): item
            for item in objects
        }


class Url(BaseField):
    pass
