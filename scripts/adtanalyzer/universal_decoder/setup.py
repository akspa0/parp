from setuptools import setup, find_packages

setup(
    name="universal_decoder",
    version="0.1.0",
    packages=find_packages(include=['universal_decoder', 'universal_decoder.*']),
    install_requires=[
        "pytest>=7.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "decode=universal_decoder.src.main:main",
        ],
    },
    package_data={
        'universal_decoder': ['*.md', '*.txt'],
    },
)