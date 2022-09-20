import importlib.metadata

try:
    __version__ = importlib.metadata.version("rmm-spoons")
except importlib.metadata.PackageNotFoundError:
    pass
