from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='cashcontrol',
    version='1.1.1',
    packages=find_packages(),
    install_requires=[
        "configparser==3.5.0",
        "pyserial==3.4",
        "jinja2==2.9.6"],
    url='',
    license='LGPL',
    author='jn',
    author_email='artel61@gmail.com',
    description='cash control package',
    long_description=open(join(dirname(__file__), 'README.rst')).read()
)
