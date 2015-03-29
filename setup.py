from setuptools import setup

setup(
    name = 'ptutils',
    version = '0.0.1',
    author = 'Rendaw',
    author_email = 'spoo@zarbosoft.com',
    url = 'https://github.com/Rendaw/ptutils',
    download_url = 'https://github.com/Rendaw/ptutils/tarball/v0.0.1',
    license = 'BSD',
    description = 'Utilities for working with polytaxis files.',
    long_description = open('readme.md', 'r').read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires = [
        'polytaxis',
        'appdirs',
        'watchdog',
        'natsort',
        'python-magic',
        'ExifRead',
        'pytaglib',
    ],
    packages = ['ptmonitor', 'ptq', 'ptimport'],
    entry_points = {
        'console_scripts': [
            'ptmonitor = ptmonitor.main:main',
            'ptq = ptq.main:main',
            'ptimport = ptimport.main:main',
        ],
    },
)
