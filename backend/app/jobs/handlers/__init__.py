REGISTRY = {}


def register(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn

    return deco


from . import clearance_pack
from . import echo
from . import pn_submit
from . import webhook_retry

__all__ = [
    "clearance_pack",
    "echo",
    "pn_submit",
    "webhook_retry",
]
