import sys

from setuptools import find_packages, setup


def get_version(filename):
    import ast

    version = None
    with open(filename) as f:
        for line in f:
            if line.startswith("__version__"):
                version = ast.parse(line).body[0].value.s
                break
        else:
            raise ValueError("No version found in %r." % filename)
    if version is None:
        raise ValueError(filename)
    return version


line = "daffy"

install_requires = [
    "termcolor",
    "decorator",
    "PyYAML",
    "python-dateutil",
    "oyaml",
    "numpy",
    "six",
    "future",
    "zuper-commons-z6",
    "zuper-ipce-z6>=6",
    "networkx>=2.2",
    "pur",  # not needed for code but for aido
    # f"aido-utils-{line}>=6.0.14",  # not needed for code but for aido
]

system_version = tuple(sys.version_info)[:3]
if system_version < (3, 7):
    install_requires.append("dataclasses")

version = get_version(filename="src/duckietown_challenges/__init__.py")

setup(
    name=f"duckietown-challenges-{line}",
    version=version,
    download_url="http://github.com/duckietown/duckietown-challenges/tarball/%s" % version,
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=install_requires,
    tests_require=[],
    # This avoids creating the egg file, which is a zip file, which makes our data
    # inaccessible by dir_from_package_name()
    zip_safe=False,
    # without this, the stuff is included but not installed
    include_package_data=True,
    entry_points={"console_scripts": []},
)
