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

    #: (str): Url of the repository. The url can point
    #: to a repository using the ssh format or https format.
    url = fields.Url(
        "Url of repository",
        availability=Version(since=1),
        default=None,
    )

    #: (str): the commit id to use
    commit = fields.String(
        "Commit of the object",
        availability=Version(since=1),
        default=None,
    )

    #: (str): the branch name to use
    branch = fields.String(
        "Branch of the object",
        availability=Version(since=1),
        default=None,
    )

    #: A private key if provided, the private key can
    #: be raw or it can be encrypted using Fernet encryption.
    private_key = fields.String(
        default=None,
    )

    #: Tell if the repo require authentication. In some cases,
    #: you could have https repositories that require extra
    #: credentials. If auth is False, then the url will not
    #: get altered to use credentials like access token provided
    #: in a credentials store.
    auth = fields.Boolean(
        default=None
    )

    @property
    def ref(self):
        """
        Returns the proper ref to use.

        By default it will try to use the following values in that
        order:

        - commit
        - branch
        - resolved odoo version or None

        Returns:
            str | None: the default ref to use.
        """
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
        """
        Converts the url of the repo in a unique path.

        The main reason is to provide a path that can be used as
        a unique identifier for the repositories. When inheriting
        services from an other manifests, all projects related to
        the same url will be inherited accordingly.

        When fetching repositories, it ensure that a project a/web
        and b/web will not be fetched into a web folder. Or to some
        extent, a github.com/a/web and gitlab.com/a/web are still
        considered as two different projects.

        Returns:
            str: the path of the repo
        """
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
    This object represent all properties that can be set
    on a manifest for odoo services.
    """

    #: (String): A string representing the name of the
    #: service configuration. For example, you may want to define
    #: a service staging and production with different settings.
    name = fields.String(
        "name",
        availability=Version(since="1")
    )

    #: (ServiceManifest): A reference to an other service manifest.
    #: It's possible to reference manifests by name. In that case, a
    #: service will be able to merge its own properties with a parent
    #: manifest configuration.
    #:
    #: For example, you may want to have a production server using the
    #: production branch of certain repositories. While a staging
    #: environment tracking the staging branch. To make things simpler,
    #: you could have all addons defined in the staging environment. But
    #: you could also define custom branches for production and keep the
    #: rest as the staging environment is using.
    inherit = fields.ProxyObject(
        "Reference to parent manifest",
        getter="get_inherited_object",
        availability=Version(since="1")
    )

    #: (OdooConfig): A field referencing an odoo configuration.
    odoo = fields.Object(
        "Odoo Configuration",
        object_class=OdooConfig,
        availability=Version(since="1")
    )

    #: (List<RepoConfig>): A list of repository configuration.
    addons = fields.Dict(
        "List of addons",
        object_class=RepoConfig,
        key="repo_path",
    )

    #: (KeyValue): A key value store of labels.
    labels = fields.Object(
        "Odoo Custom Options",
        object_class=KeyValue,
        availability=Version(since=1)
    )

    #: (KeyValue): A key value store of environment variables.
    env = fields.Object(
        "Odoo Custom Options",
        object_class=KeyValue,
        availability=Version(since=1)
    )

    def get_inherited_object(self, key):
        """
        Returns:
            ServiceManifest: Related service manifest given by its name.
        """
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
        """
        This service manifest with all of its
        properties resolved against the inherit property.

        For example, if you had a service that inherits from an
        other one and each of them had different addons configured.
        It would let you combine all configurations together.

        The value of this property would be a new ServiceManifest
        that has all addons of self and of inherit (recursively).

        Returns:
            ServiceManifest: ServiceManifest that is an extension of inherit
        """
        return self.extend(self.inherit)

    def extend(self, other):
        """
        Creates a new ServiceManifest that extend the other one.

        Args:
            other (ServiceManifest): The other manifest to inherit from.

        Returns:
            (ServiceManifest): A new ServiceManifest
        """
        if not other:
            return self

        return ServiceManifest({
            "name": self.name,
            "odoo": self.resolved_prop('odoo'),
            "addons": self.resolved_prop('addons'),
            "labels": self.resolved_prop('labels'),
            "env": self.resolved_prop('env'),
        })

    def to_dict(self):
        """
        Returns a dict representing the data in this object.

        Returns:
            dict: Dict containing all properties of this object.
        """
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
    #: (dict): Dictionary of service manifest by their name
    services = fields.Dict(
        "List of services",
        object_class=ServiceManifest,
        key="name"
    )

    def to_dict(self):
        """
        Returns a dict representing the data in this object.

        Returns:
            dict: Dict containing all properties of this object.
        """
        return {
            "services": {
                key: val.to_dict()
                for key, val in self.services.items()
            }
        }
