from setuptools import setup, find_packages

setup(
    name="downloader",
    version="0.1.0",
    description="A sample Python package",
    packages = find_packages(), # Automatically find packages in the current directory
    py_modules=["cli"],
    author= "Anurag Shukla",
    install_requires=[requirements.strip() for requirements in open("requirements.txt").readlines()],
    author_email="rishanu68@gmail.com",
    entry_points={
        "console_scripts": [
            "downloader=cli:cli",  # Entry point for the CLI module:function
        ],
    },
)