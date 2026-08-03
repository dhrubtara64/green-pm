"""conftest.py — adds supply-chain-engine to sys.path and isolates app namespace."""
import pathlib
import sys

_SERVICE = str(pathlib.Path(__file__).parents[3] / "services" / "supply-chain-engine")
for _key in list(sys.modules.keys()):
    if _key == "app" or _key.startswith("app."):
        del sys.modules[_key]
if _SERVICE in sys.path:
    sys.path.remove(_SERVICE)
sys.path.insert(0, _SERVICE)
