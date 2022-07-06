import giturlparse

from . import fields
from . import models


class ValidationError(Exception):
    pass


class Version(object):

    def __init__(self, since, until=None):
        self.since = since
        self.until = until


class KeyValue(models.Extendable, models.ParentedObject, models.BaseModel):
    def extend(self, other):
        options = self._data.copy()
        options.update(other._data if other and other._data else {})
        return KeyValue(options)

    def to_dict(self):
        return self._data.copy()


class RepoConfig(models.ParentedObject, models.Extendable, models.BaseModel):

    url = fields.Url(
        "Url of repository",
        availability=Version(since=1),
        default=None,
    )

    commit = fields.String(
        "Commit of the object",
        availability=Version(since=1),
        default=None,
    )

    branch = fields.String(
        "Branch of the object",
        availability=Version(since=1),
        default=None,
    )

    private_key = fields.String(
        default=None,
    )

    auth = fields.Boolean(
        default=None
    )

    @property
    def ref(self):
        service = self.get_parent(ServiceManifest)

        if (
            service and
            service.resolved.odoo and
            service.resolved.odoo.version
        ):
            default = service.resolved.odoo.version
        else:
            default = None

        return self.commit or self.branch or default

    @property
    def repo_path(self):
        url = giturlparse.parse(self.url.lower())

        if url.valid:
            path = "_".join([
                url.host.replace('.', '_'),
                url.owner.replace('/', '_'),
                url.repo.replace('/', '_')
            ])
        else:
            path = self.url

        return path

    def extend(self, other):
        if not other:
            return self

        return RepoConfig({
            "url": other.url or self.url,
            "commit": other.commit or self.commit,
            "branch": other.branch or self.branch,
            "private_key": other.private_key or self.private_key,
        })

    def to_dict(self):
        return {
            "url": self.url,
            "commit": self.commit,
            "branch": self.branch,
            "ref": self.ref,
            "private_key": self.private_key
        }


class OdooConfig(models.ParentedObject, models.Extendable, models.BaseModel):
    version = fields.String()

    repo = fields.Object(
        "Repository Configuration",
        object_class=RepoConfig,
        availability=Version(since=1)
    )

    options = fields.Object(
        "Odoo Custom Options",
        object_class=KeyValue,
        availability=Version(since=1)
    )

    def extend(self, other):
        if not other:
            return self

        return OdooConfig({
            "version": (
                other.version
                if other.version
                else self.version
            ),
            "repo": (
                other.repo.extend(self.repo)
                if other.repo
                else self.repo
            ),
            "options": (
                other.options.extend(self.options)
                if other.options
                else self.options
            )
        })

    def to_dict(self):
        return {
            "version": self.version,
            "repo": self.repo.to_dict() if self.repo else {},
            "options": self.options.to_dict() if self.options else {}
        }


class ManifestProxy(models.ParentedObject, models.BaseModel):
    reference = fields.String()

    @classmethod
    def parse(klass, data):
        return ManifestProxy({"reference": data})


class ServiceManifest(
    models.ParentedObject,
    models.Extendable,
    models.BaseModel
):
    """
    ServiceManifest
    ===============

    This object represent all properties that can be set
    on a manifest for odoo services.

    Properties:

    name (String): A string representing the name of the
        service configuration. For example, you may want to define
        a service staging and production with different settings.

    inherit (ServiceManifest): A reference to an other service manifest.
        It's possible to reference manifests by name. In that case, a service
        will be able to merge its own properties with a parent manifest
        configuration.

        For example, you may want to have a production server using the
        production branch of certain repositories. While a staging environment
        tracking the staging branch. To make things simpler, you could have all
        addons defined in the staging environment. But you could also define
        custom branches for production and keep the rest as the staging
        environment is using.

    odoo (OdooConfig): A field referencing an odoo configuration.

    addons (List<RepoConfig>): A list of repository configuration.

    labels (KeyValue): A key value store of labels.

    env (KeyValue): A key value store of environment variables.
    """
    name = fields.String(
        "name",
        availability=Version(since="1")
    )

    inherit = fields.ProxyObject(
        "Reference to parent manifest",
        getter="get_inherited_object",
        availability=Version(since="1")
    )

    odoo = fields.Object(
        "Odoo Configuration",
        object_class=OdooConfig,
        availability=Version(since="1")
    )

    addons = fields.Dict(
        "List of addons",
        object_class=RepoConfig,
        key="repo_path",
    )

    labels = fields.Object(
        "Odoo Custom Options",
        object_class=KeyValue,
        availability=Version(since=1)
    )

    env = fields.Object(
        "Odoo Custom Options",
        object_class=KeyValue,
        availability=Version(since=1)
    )

    def get_inherited_object(self, key):
        parent = self.get_parent(ServiceManifests)
        return parent.services[key]

    # TODO refactor to make auto extandable objects
    # Guess how they can be extended without specifying
    # properties.
    def resolved_prop(self, prop_name):
        if not self.inherit:
            return getattr(self, prop_name)

        other_val = self.inherit.resolved_prop(prop_name)
        self_val = getattr(self, prop_name)

        if not other_val:
            return self_val

        if not self_val:
            return other_val

        # TODO return Extendable Collections in field with list/dict
        if isinstance(other_val, models.Extendable):
            return other_val.extend(self_val)
        elif isinstance(other_val, dict):
            ret_val = other_val.copy()
            for key, value in self_val.items():
                if (
                    key in ret_val and
                    isinstance(ret_val[key], models.Extendable)
                ):
                    ret_val[key] = ret_val[key].extend(value)
                else:
                    ret_val[key] = value
            return ret_val
        elif isinstance(other_val, list):
            return other_val + ret_val
        else:
            print("whoa")

    @property
    def resolved(self):
        return self.extend(self.inherit)

    def extend(self, other):
        if not other:
            return self

        return ServiceManifest({
            "name": self.name,
            "odoo": self.resolved_prop('odoo'),
            "addons": self.resolved_prop('addons'),
            "labels": self.resolved_prop('labels'),
            "env": self.resolved_prop('env'),
        })

    # To dict should be guessable from properties defined on class
    def to_dict(self):
        inherit = (
            self._data['inherit']['ref']
            if 'inherit' in self._data
            else None
        )

        addons = self.addons or {}

        vals = {
            "name": self.name,
            "addons": {
                key: val.to_dict()
                for key, val in addons.items()
            }
        }

        if inherit:
            vals['inherit'] = inherit

        for attr in ['odoo', 'env', 'labels']:
            val = getattr(self, attr)
            if val:
                vals[attr] = val.to_dict()

        return vals


class ServiceManifests(models.BaseModel):
    services = fields.Dict(
        "List of services",
        object_class=ServiceManifest,
        key="name"
    )

    def to_dict(self):
        return {
            "services": {
                key: val.to_dict()
                for key, val in self.services.items()
            }
        }
