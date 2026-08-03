import pathlib
import sys

_SERVICE = str(pathlib.Path(__file__).parents[3] / "services" / "api-gateway")

# Clear any cached 'app' modules from a prior service, then place this service first
for _key in list(sys.modules.keys()):
    if _key == "app" or _key.startswith("app."):
        del sys.modules[_key]

if _SERVICE in sys.path:
    sys.path.remove(_SERVICE)
sys.path.insert(0, _SERVICE)
