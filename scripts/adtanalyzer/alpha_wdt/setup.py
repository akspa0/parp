"""
Setup script for wdt_adt_parser package.
"""
from setuptools import setup, find_packages

setup(
    name="wdt_adt_parser",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'sqlite3',
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A library for parsing WoW WDT/ADT files",
    long_description=open('wdt_adt_parser/README.md').read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)