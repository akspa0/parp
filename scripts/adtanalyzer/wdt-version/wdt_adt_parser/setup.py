"""
Setup configuration for WDT/ADT Parser package
"""
from setuptools import setup, find_packages

setup(
    name="wdt_adt_parser",
    version="0.1.0",
    packages=find_packages(),
    description="Universal parser for WoW WDT/ADT files",
    author="Roo",
    python_requires=">=3.7",
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)