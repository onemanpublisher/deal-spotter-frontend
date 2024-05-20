from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
import sys
import platform
import sys
import os
import logging
from datetime import timedelta


system = platform.system()
if system == "Linux":
    sys.path.append("/root/Deal_Spotter")
elif system == "Windows":
    sys.path.append("G:\\10. Programmierung\\6. Python OneManPublisher\\Deal_Spotter")
from scripts.utils.omp_logging import OmpLogging

db = SQLAlchemy()
# cache = Cache(config={'CACHE_TYPE': 'simple'})  #! used for simple cache system
cache = Cache(config={'CACHE_TYPE': 'redis', 'CACHE_REDIS_URL': 'redis://localhost:6379/0'})

OmpLogging(folder_start_name="deal_spotter_frontend")
flask_env = os.environ.get("FLASK_ENV")

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'K*W85PiGLDjRqa$7Enhst8y@K&Bn5iPCNX!*mHBQ*cinoG3LD*'
    if flask_env == "development":  # used for debugger
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../database/db.sqlite'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../../database/db.sqlite'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=14)  # Adjust the duration as needed
    app.config['SESSION_PERMANENT'] = False

    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS to use SameSite=None
    app.config['SQLALCHEMY_POOL_SIZE'] = 20
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30  # Optional, set your preferred timeout
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = 20

    # Enable HSTS with a max-age value and includeSubDomains
    @app.after_request
    def add_hsts_header(response):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404_not_found.html'), 404

    # @app.before_request
    # def track_access():
    #     page_url = request.path
    #     if not page_url.startswith('/static'):
    #         ip_address = request.remote_addr
    #         logging.info(f"Access from {ip_address} on {page_url}")
        # access = Access.query.filter_by(page_url=page_url, ip_address=ip_address).first()
        # if access:
        #     access.total_accesses += 1
        # else:
        #     new_access = Access(page_url=page_url, ip_address=ip_address, total_accesses=1)
        #     db.session.add(new_access)

        # db.session.commit()

    db.init_app(app)
    cache.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Du musst eingeloggt sein, um diese Seite zu sehen!"
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .methods import methods as methods_blueprint
    app.register_blueprint(methods_blueprint)
    
    from .tools import tools as tools_blueprint
    app.register_blueprint(tools_blueprint)

    return app
