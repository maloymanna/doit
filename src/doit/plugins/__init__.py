import importlib
import os
import pkgutil
from .base import Plugin

def load_plugins() -> dict[str, Plugin]:
    registry = {}
    package = __name__
    package_path = os.path.dirname(__file__)

    for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg or module_name == "base":
            continue
        module = importlib.import_module(f"{package}.{module_name}")
        for obj in module.__dict__.values():
            if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin:
                plugin = obj()
                for cap in plugin.capabilities:
                    registry[cap] = plugin
    return registry
