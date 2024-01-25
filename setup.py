from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
with open('requirements.txt') as f:
    requirements_txt = f.read().splitlines()

setup(
    name='latio',
    version='v1.0.0',
    url='https://github.com/latiotech/LAST',
    license='GPL-3.0 license',
    author='James Berthoty',
    author_email='james@latio.tech',
    description='Latio Application Security Tester - Uses OpenAPI to scan for security issues in code changes',
    install_requires=requirements_txt,
    entry_points = {
            'console_scripts': ['latio = latio.core:main'],
        },
    long_description=long_description,
    long_description_content_type='text/markdown'
)
