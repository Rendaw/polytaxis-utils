from setuptools import setup

setup(
    name = 'ptutils',
    version = '0.0.1',
    author = 'Rendaw',
    author_email = 'spoo@zarbosoft.com',
    packages = ['ptmonitor', 'ptq'],
    url = 'https://github.com/Rendaw/ptutils',
    download_url = 'https://github.com/Rendaw/ptutils/tarball/v0.0.1',
    license = 'BSD',
    description = 'Utilities to work with polytaxis files.',
    long_description = open('readme.md', 'r').read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ],
    dependency_links = [
        'https://github.com/Rendaw/polytaxis/tarball/master#egg=polytaxis-git',
    ],
    install_requires = [
        'polytaxis',
        #'PyQt5',
        'appdirs',
        'watchdog',
        'natsort',
        'python-magic',
        'ExifRead',
        'pytaglib',
    ],
    entry_points = {
        'console_scripts': [
            'ptmonitor = ptmonitor.main:main',
            'ptq = ptq.main:main',
            'ptimport = ptimport.main:main',
        ],
    },
)
