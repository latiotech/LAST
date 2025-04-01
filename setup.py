from setuptools import setup
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()
with open('requirements.txt') as f:
    requirements_txt = f.read().splitlines()

setup(
    name='latio',
    version='v1.2.5',
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
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Security',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    package_dir={'': 'src'},
    packages=['latio'],
    include_package_data=True,
)
