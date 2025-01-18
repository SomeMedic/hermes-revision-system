from setuptools import setup, find_packages

# Читаем README.md с явным указанием кодировки UTF-8
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Определяем зависимости
install_requires = [
    "click>=8.1.7",
    "watchdog>=3.0.0",
    "python-dotenv>=1.0.0",
    "graphviz>=0.20.1",
]

dev_requires = [
    "pytest>=7.4.0",
    "black>=23.12.1",
    "flake8>=7.0.0",
]

setup(
    name="hermes-revision-system",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
    },
    entry_points={
        "console_scripts": [
            "hrs=cli.hrs_cli:cli",
        ],
    },
    author="SomeMedic",
    author_email="maxg2015maxg@gmail.com",
    description="Hermes Revision System - современная система контроля версий",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="hrs, hermes, version control, git, vcs, система контроля версий",
    url="https://github.com/SomeMedic/hermes-revision-system",
    project_urls={
        "Bug Tracker": "https://github.com/SomeMedic/hermes-revision-system/issues",
        "Documentation": "https://github.com/SomeMedic/hermes-revision-system/wiki",
        "Source Code": "https://github.com/SomeMedic/hermes-revision-system",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control",
        "Topic :: Software Development :: Version Control :: Git",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: Russian",
        "Natural Language :: English",
    ],
    python_requires=">=3.8",
)