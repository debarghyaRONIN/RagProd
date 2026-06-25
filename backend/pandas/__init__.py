# Mock pandas package to bypass WDAC / AppLocker restrictions on DLL binaries

class DataFrame:
    """Mock DataFrame class for PyMilvus type checks."""
    def __init__(self, *args, **kwargs):
        pass

class Series:
    """Mock Series class for PyMilvus type checks."""
    def __init__(self, *args, **kwargs):
        pass

__version__ = "2.2.0"
