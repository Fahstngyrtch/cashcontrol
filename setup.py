from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='cashcontrol',
    version='1.1.6',
    packages=find_packages(),
    install_requires=[
        "configparser",
        "pyserial",
        "jinja2"],
    url='',
    license='LGPL',
    author='jn',
    author_email='artel61@gmail.com',
    description='cash control package',
    long_description=open(join(dirname(__file__), 'README.rst')).read()
)
