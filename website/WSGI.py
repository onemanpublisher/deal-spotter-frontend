# use this script to start gunicorn with gunicorn --bind 0.0.0.0:80 WSGI:application
# only working on linux systems
from project import create_app
application = create_app()
