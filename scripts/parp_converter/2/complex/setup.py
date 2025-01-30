from setuptools import setup, find_packages

setup(
    name="wdt_adt_parser",
    version="0.1.0",
    description="Universal parser for WoW WDT/ADT files with database support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/wdt_adt_parser",
    packages=find_packages(),
    install_requires=[
        "typing-extensions>=4.0.0",  # For Python <3.8 compatibility
        "numpy>=1.20.0",            # For efficient array operations
        "mmap-backed-array>=0.5.0", # For memory-mapped array support
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0.0",
            "mypy>=0.900",
            "pylint>=2.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "wdt-parser=example:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Games/Entertainment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    include_package_data=True,
    zip_safe=False,
)