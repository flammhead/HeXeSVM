from codecs import open
from os import path
from setuptools import find_packages, setup

# load README
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="HeXeSVM",
    version="0.0.1",
    description="Secure voltage management for HeXe",
    long_description=long_description,
    author="Florian Joerg",
    author_email="florian.joerg@mpi-hd.mpg.de",
    packages=find_packages(exclude=["bin"])
)

