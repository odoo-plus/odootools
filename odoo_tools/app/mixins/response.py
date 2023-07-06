class LaxCookieMixin(object):
    """
    Fix the set_cookie method to use the Lax samesite
    value as the implicit default value changed in recent
    browsers.
    """
    def set_cookie(
        self,
        key,
        value='',
        max_age=None,
        expires=None,
        path='/',
        domain=None,
        secure=None,
        httponly=False,
        samesite=None
    ):
        # Lax is the new default for samesite, unfortunately
        # when setting samesite=None, it simply ignores the
        # value None instead of outputting the value as it is
        # set.
        # As a result werkzeug can only set it to:

        # Lax explicit
        # Strict explicit
        # Lax implicit
        if samesite is None:
            samesite = 'Lax'

        return super().set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite
        )


class SecureCookieMixin(object):
    """
    Define an secure cookie unless asked otherwise.
    """
    def set_cookie(
        self,
        key,
        value='',
        max_age=None,
        expires=None,
        path='/',
        domain=None,
        secure=None,
        httponly=False,
        samesite=None
    ):
        if secure is None:
            secure = True
        else:
            secure = secure or False

        return super().set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite
        )


class InsecureCookieMixin(object):
    """
    Define an insecure cookie unless asked otherwise.
    """
    def set_cookie(
        self,
        key,
        value='',
        max_age=None,
        expires=None,
        path='/',
        domain=None,
        secure=None,
        httponly=False,
        samesite=None
    ):
        if secure is None:
            secure = False
        else:
            secure = secure or True

        return super().set_cookie(
            key=key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite
        )