"""Basic tests to verify CI setup."""

def test_basic():
    """Basic test to verify pytest is working."""
    assert True

def test_python_version():
    """Verify Python version is compatible."""
    import sys
    assert sys.version_info >= (3, 9), "Python version should be 3.9 or higher"

def test_required_packages():
    """Verify required packages are installed."""
    import importlib
    
    required_packages = [
        'fastapi',
        'redis',
        'aiohttp',
        'websockets',
        'requests'
    ]
    
    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            assert False, f"Required package {package} is not installed" 