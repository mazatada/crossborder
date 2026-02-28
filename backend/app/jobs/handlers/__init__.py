REGISTRY = {}


def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn

    return deco

from . import clearance_pack  # noqa: E402, F401
from . import echo  # noqa: E402, F401
from . import pn_submit  # noqa: E402, F401
from . import webhook_retry  # noqa: E402, F401
from . import webhook_dispatch  # noqa: E402, F401
