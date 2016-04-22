from setuptools import setup, find_packages
import timeseries


setup(
    author="Anthony",
    name="django-timeseries",
    version=timeseries.__version__,
    packages=find_packages(exclude=["test*", ]),
    url="https://github.com/anthonyalmarza/timeseries",
    description=(
        "`timeseries`."
    ),
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    keywords=['timeseries', ],
    install_requires=['django', 'psycopg2'],
    extras_require={'dev': ['ipdb', 'mock']},
    include_package_data=True
)
