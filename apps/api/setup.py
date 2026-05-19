#!/usr/bin/env python
"""Setup script for backward compatibility with older pip versions.

This package uses pyproject.toml for configuration. This setup.py
is provided for compatibility with older tools that don't support
PEP 517/518 builds.
"""

from setuptools import setup

if __name__ == "__main__":
    setup()
