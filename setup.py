"""
Setup script for SCL Protocol package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text() if readme_file.exists() else ''

setup(
    name='scl-protocol',
    version='0.1.0',
    author='Matthias Peplow',
    description='Python library for LyTech LED controller communication via SCL/SuperComm protocol',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/scl-protocol',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'Pillow>=9.0.0',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: System :: Hardware',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    keywords='led controller lytech scl2008 supercomm hardware protocol library',
)
