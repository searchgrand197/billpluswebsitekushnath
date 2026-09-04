"""
WSGI config for the merged Kushnath project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kushnath.settings")

application = get_wsgi_application()
