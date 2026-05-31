from __future__ import annotations

from importlib import import_module

_MODULE_NAMES = ("auth", "base_demo", "cleanup", "full_demo", "rag_demo", "entrypoints")
_modules = [import_module(f"{__name__}.{name}") for name in _MODULE_NAMES]
_public = {}
for _module in _modules:
    for _name, _value in vars(_module).items():
        if _name.startswith("__"):
            continue
        _public[_name] = _value
for _module in _modules:
    vars(_module).update(_public)
globals().update(_public)
__all__ = sorted(_public)
