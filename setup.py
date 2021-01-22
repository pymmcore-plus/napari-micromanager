from setuptools import setup, find_packages

setup(
    name="napari-micromanager",
    version="0.0.1",
    description="A python gui for micro-manager",
    author="Federico Gasparoli",
    author_email="federico.gasparoli@gmail.com",
    url="https://github.com/fdrgsp/micromanager.git",
    packages=find_packages(),
    install_requires=[
        'napari[all]',
        'numpy',
        'scikit-image',
        'matplotlib',      
        'qtpy',
        'pyqt5<5.15',
        'pymmcore',
        'pyfirmata2'
        ]
)
