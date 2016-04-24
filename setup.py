from setuptools import setup, find_packages
import timeseries


setup(
    author="Anthony Almarza",
    name="django-timeseries",
    version=timeseries.__version__,
    packages=find_packages(exclude=["test*", ]),
    url="https://github.com/anthonyalmarza/timeseries",
    description=(
        "`timeseries` is a set of django application tools designed to "
        "facilitate the collation and maintenance of timeseries data."
    ),
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    keywords=['timeseries', 'django', 'data', 'latest'],
    install_requires=['django', 'psycopg2'],
    extras_require={'dev': ['ipdb', 'mock', 'tox', 'coverage']},
    include_package_data=True
)
