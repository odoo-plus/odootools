if 'IrHttp' not in globals():
    IrHttp = None


@classmethod
def _post_dispatch(cls, response):
    pass


@classmethod
def _pre_dispatch(cls, rule, args):
    pass


IrHttp._pre_dispatch = _pre_dispatch
IrHttp._post_dispatch = _post_dispatch
