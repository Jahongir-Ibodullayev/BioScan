# gevent monkey-patch — but skip ssl. Patching ssl on Python 3.12
# breaks SSLContext.minimum_version (urllib3 / requests sets it at
# import time and the patched descriptor recurses forever).
# Nginx terminates TLS for inbound, and outbound HTTPS via requests
# is fine without gevent ssl-patching.
try:
    from gevent import monkey

    monkey.patch_all(ssl=False)
except ImportError:
    pass

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "togai.settings")

application = get_wsgi_application()
