# gevent must monkey-patch ssl/socket BEFORE Django (and ultimately
# urllib3/requests) imports them — otherwise stdlib ssl.SSLContext
# property descriptors recurse forever on Python 3.12.
try:
    from gevent import monkey

    monkey.patch_all()
except ImportError:
    pass

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "togai.settings")

application = get_wsgi_application()
