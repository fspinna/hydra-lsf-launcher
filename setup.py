from setuptools import find_namespace_packages, setup

with open("README.md") as fh:
    LONG_DESC = fh.read()
    setup(
        version="0.1.0",
        name="hydra-lsf-launcher",
        author="Francesco Spinnato",
        author_email="francesco.spinnato@di.unipi.it",
        description="Lsf Hydra Launcher plugin",
        long_description=LONG_DESC,
        long_description_content_type="text/markdown",
        packages=find_namespace_packages(include=["hydra_plugins.*"]),
        classifiers=[
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Operating System :: OS Independent",
        ],
        install_requires=[
            "hydra-core",
        ],
        include_package_data=True,
    )
