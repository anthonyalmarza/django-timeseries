import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 'tdzf@9g8lofi@lo$=126jrka1ydzjix^!8j)vg$6cd+kz^ei5h'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'tests'
]


test_db = os.environ.get('TEST_DB_CONFIG', 'postgres')
db_user = os.environ.get('TEST_DB_USER', os.environ.get('USER', ''))
db_name = 'timerseries_tests' + os.environ.get('TEST_DB_NAME', '')

DB_CONFIGS = {
    # N.B. sqlite doesn't support DISTINCT ON for some reason... ???
    'postgres': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': ''
    }
}

DATABASES = {
    'default': DB_CONFIGS.get(test_db)
}
