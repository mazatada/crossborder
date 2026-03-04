REGISTRY = {}


def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn

    return deco


from . import clearance_pack  # noqa: E402
from . import echo  # noqa: E402
from . import pn_submit  # noqa: E402
from . import webhook_retry  # noqa: E402
from . import hs_classify

__all__ = [
    "clearance_pack",
    "echo",
    "pn_submit",
    "webhook_retry",
    "hs_classify"
]
