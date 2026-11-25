"""Public compatibility exports, loaded only when their entry point is requested.

Focused sklearn research does not depend on native sequence-model or paper harness
startup. Importing the historical public names still returns the original objects.
"""
from importlib import import_module

__all__ = ['MethodCard', 'MethodCardAgent', 'PaperTextLoader', 'method_card_to_paper_spec', 'run_harness']


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = '.harness' if name == 'run_harness' else '.method_cards'
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
