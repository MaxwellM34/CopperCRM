from .base import BaseConfig


class LocalConfig(BaseConfig):
    # PostgreSQL configuration
    PG_HOST = 'localhost'
    PG_PORT = 5432
    PG_USER = 'postgres'
    PG_PASS = 'Sk1b1d167!89*69'
    PG_DB = 'postgres'

    # Actual cloud config
    GOOGLE_AUDIENCE = (
        '93240326522-edc30scocjt3utnqlsfvgfqk8oj48brn.apps.googleusercontent.com'
    )
    SERVER_URL = 'localhost'
    TORTOISE_ORM = {
        'connections': {
            'default': f'postgres://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}'
        },
        'apps': {
            'models': {
                'models': ['models', 'aerich.models'],
                'default_connection': 'default',
            },
        },
    }
