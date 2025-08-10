"""
Setup script for EKS Upgrade Assessment Toolkit
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="eks-upgrade-assessment-toolkit",
    version="1.0.0",
    author="AWS Customer",
    description="A comprehensive toolkit to assess EKS cluster readiness for upgrades",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "": ["templates/*.j2", "templates/**/*.j2"],
    },
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "eks-upgrade-assess=main:cli",
            "eks-metadata-collect=cluster_metadata_generator:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="aws eks kubernetes upgrade assessment",
    project_urls={
        "Documentation": "https://github.com/aws-samples/eks-upgrade-assessment-toolkit",
        "Source": "https://github.com/aws-samples/eks-upgrade-assessment-toolkit",
        "Tracker": "https://github.com/aws-samples/eks-upgrade-assessment-toolkit/issues",
    },
)
