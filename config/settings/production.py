# ruff: noqa

from config.settings.common import *  # noqa : F403

ENABLE_EMAIL = True


DEBUG = True


############################
#       SILK SETTINGS      #
############################
ENABLE_SILK = False



ALLOWED_HOSTS = [
    "genzplaying.com",
    "www.genzplaying.com",
    "api.genzplayzone.com",
    "dev.api.genzplayzone.com",
    "127.0.0.1",
    "localhost",
]