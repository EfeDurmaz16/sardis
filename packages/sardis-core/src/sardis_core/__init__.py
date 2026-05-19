"""Preferred import namespace for the Sardis core package.

The historical import package is ``sardis_v2_core``. Keep it available for
compatibility, but use ``sardis_core`` in new docs and examples.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import sys
from types import ModuleType

import sardis_v2_core as _legacy
from sardis_v2_core import *  # noqa: F403

__all__ = getattr(_legacy, "__all__", [name for name in dir(_legacy) if not name.startswith("_")])
__version__ = getattr(_legacy, "__version__", "0.3.0")

__path__ = _legacy.__path__


class _LegacyCoreAliasImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Map `sardis_core.*` imports to the existing `sardis_v2_core.*` modules."""

    marker = "sardis-core-alias-importer"

    def find_spec(
        self,
        fullname: str,
        path: object | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if not fullname.startswith("sardis_core."):
            return None
        legacy_name = fullname.replace("sardis_core", "sardis_v2_core", 1)
        legacy_spec = importlib.util.find_spec(legacy_name)
        if legacy_spec is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            self,
            origin=legacy_spec.origin,
            is_package=legacy_spec.submodule_search_locations is not None,
        )

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        legacy_name = spec.name.replace("sardis_core", "sardis_v2_core", 1)
        return importlib.import_module(legacy_name)

    def exec_module(self, module: ModuleType) -> None:
        alias_name = module.__name__.replace("sardis_v2_core", "sardis_core", 1)
        sys.modules[alias_name] = module


if not any(getattr(finder, "marker", None) == _LegacyCoreAliasImporter.marker for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyCoreAliasImporter())

for _name, _module in list(sys.modules.items()):
    if _name.startswith("sardis_v2_core."):
        sys.modules.setdefault(_name.replace("sardis_v2_core", "sardis_core", 1), _module)
