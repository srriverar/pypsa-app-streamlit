"""Package metadata from pyproject.toml"""

from importlib.metadata import metadata

_metadata = metadata("pypsa-app")
__version__ = _metadata["Version"]
__description__ = _metadata["Summary"]
