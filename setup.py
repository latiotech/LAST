from setuptools import setup
import os
from setuptools import setup

with open('requirements.txt') as f:
    requirements_txt = f.read().splitlines()

setup(
    name='LAST',
    version='v0.0.2',
    packages=[''],
    url='https://github.com/latiotech/LAST',
    license='GPL-3.0 license',
    author='James Berthoty',
    author_email='confusedcrib@gmail.com',
    description='Latio Application Security Tester',
    install_requires=requirements_txt,
    entry_points = {
            'console_scripts': ['LAST = LAST:main'],
        },

)
