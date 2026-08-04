from os import environ

# One entry point; participants choose language (English / 简体中文) on the first page.
SESSION_CONFIGS = [
    dict(
        name='reliance',
        display_name='Consensus study / 多模型一致性研究',
        app_sequence=['reliance'],
        num_demo_participants=6,
    ),
]

# A room gives a single, stable participant-facing link for recruitment
# (share the room's participant URL; each click starts a new participant at the language page).
ROOMS = [
    dict(
        name='reliance',
        display_name='Consensus study / 多模型一致性研究',
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD', 'admin')

SECRET_KEY = environ.get('OTREE_SECRET_KEY', 'dev-only-secret-key-change-me')
INSTALLED_APPS = ['otree']
