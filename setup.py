from setuptools import setup

setup(
    name='mplcolortext',
    version='0.1',
    description='Coloured text for matplotlib',
    url='git@github.com:alastairgarner/mplcolortext.git',
    author='Alastair G',
    author_email='garneralastair@gmail.com',
    license='MIT',
    packages=['mplcolortext'],
    install_requires=[
        'git+https://git@github.com/alastairgarner/mpltransform.git',
    ],
    zip_safe=False
)