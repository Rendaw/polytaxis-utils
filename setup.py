from setuptools import setup

setup(
    name = 'ptmon',
    version = '0.0.1',
    author = 'Rendaw',
    author_email = 'spoo@zarbosoft.com',
    packages = ['ptmon', 'ptman'],
    url = 'https://github.com/Rendaw/ptmon',
    download_url = 'https://github.com/Rendaw/ptmon/tarball/v0.0.1',
    license = 'BSD',
    description = 'Index files and browse polytaxis tags.',
    long_description = open('readme.md', 'r').read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires = [
        'PyQt5',
        'appdirs',
        'watchdog',
    ],
    entry_points = {
        'console_scripts': [
            'ptmon = ptmon.ptmon:main',
        ],
    }
)
