import sys
import os

# Add your project directory to the sys.path
project_home = '/home/yacinedev84/mysite'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import flask app but need to call it "application" for WSGI to work
from flask_app import app as application
