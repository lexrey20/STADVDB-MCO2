from setuptools import setup

setup(
    name='STADVDB-MCO2',
    version='1.0',
    packages=['MCO2'],
    url='https://github.com/lexrey20/STADVDB-MCO2',
    license='',
    author='Lexrey D. Porciuncula',
    author_email='lexrey_porciuncula@dlsu.edu.ph',
    description='Distributed Database MCO2',
    install_requires=['sqlalchemy', 'flask', 'flask_sqlalchemy'],
)
