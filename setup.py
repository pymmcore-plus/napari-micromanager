from setuptools import setup, find_packages

setup(
    name="micromanager",
    version="0.0.1",
    description="A micromanager gui in python.",
    author="Federico Gasparoli",
    author_email="federico.gasparoli@gmail.com",
    url="https://github.com/fdrgsp/micromanager.git",
    packages=find_packages(),
    install_requires=[
        'napari[all]',
        'numpy',
        'scikit-image',
        'matplotlib'
        ]
)
