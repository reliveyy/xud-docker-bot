from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md") as f:
    long_description = f.read()

setup(
    name="xud-docker-bot",
    version="1.0.0.dev54",
    description="A bot for xud-docker",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/exchangeunion/xud-docker-bot",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8"
)
