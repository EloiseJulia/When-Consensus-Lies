from os import environ

SESSION_CONFIGS = [
    dict(
        name='reliance',
        display_name='Human-reliance study (fake multi-model consensus)',
        app_sequence=['reliance'],
        num_demo_participants=6,   # multiple of 3 -> balanced Latin-square groups
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=2.00,       # ~$2 for ~10 min (<CONFIRM>)
    doc="",
)

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False

ROOMS = []
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD', 'admin')

SECRET_KEY = environ.get('OTREE_SECRET_KEY', 'dev-only-secret-key-change-me')
INSTALLED_APPS = ['otree']
