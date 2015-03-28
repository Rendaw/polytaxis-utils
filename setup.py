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
    description = 'Index files and browse polytaxis tags.',
    long_description = open('readme.md', 'r').read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
    ],
    install_requires = [
        #'PyQt5',
        'appdirs',
        'watchdog',
        'polytaxis',
    ],
    entry_points = {
        'console_scripts': [
            'ptmonitor = ptmonitor.main:main',
            'ptq = ptq.main:main',
        ],
    }
)
