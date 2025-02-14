# setup.py
from setuptools import setup, find_packages

setup(
    name="adt_analyzer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],  # Add any dependencies here
    python_requires=">=3.7",
    author="akspa0",
    author_email="akspa0@immoralhole.com",
    description="A tool for analyzing World of Warcraft ADT files",
    keywords="wow, adt, analysis",
    entry_points={
        'console_scripts': [
            'analyze-adt=scripts.analyze_adt:main',
        ],
    }
)
