if 'IrHttp' not in globals():
    IrHttp = None


def new_dispatch(cls):
    return None


IrHttp._dispatch = classmethod(new_dispatch)
