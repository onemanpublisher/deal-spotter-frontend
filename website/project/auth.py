from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, Locations
from passlib.hash import scrypt
from . import db
from .tools import Tools, Database
from datetime import datetime, timezone
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


auth = Blueprint('auth', __name__)

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

@auth.route('/einloggen')
def login():
    return render_template('login.html')

@auth.route('/einloggen', methods=['POST'])
@limiter.limit("10 per hour")
def login_post():
    input_user = request.form.get('user')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    if Tools.email_check(input_user):  # check if user is email
        user = User.query.filter_by(email=input_user).first()
    else:
        user = User.query.filter_by(name=input_user).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not scrypt.verify(password, user.password):
        flash('Bitte überprüfe deine Anmeldedaten und versuche es erneut.', category="error")
        return redirect(url_for('auth.login'))  # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    current_user.last_login = current_date
    current_user.total_logins = (user.total_logins or 0) + 1
    db.session.commit()
    flash('Du hast dich erfolgreich angemeldet!', category="success")
    return redirect(url_for('main.index'))

@auth.route('/registrieren')
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    else:
        return render_template('signup.html')

@auth.route('/registrieren', methods=['POST'])
@limiter.limit("15 per hour")
def signup_post():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    input_user = request.form.get('name')
    input_email = request.form.get('email')
    input_password = request.form.get('password')


    if len(input_user) < 3:
        flash('Der Name muss mindestens 3 Zeichen lang sein.', category="error")
        return redirect(url_for('auth.signup'))

    if not Tools.password_check(input_password):
        flash('Das Passwort muss mindestens 8 Zeichen und eine Ziffer enthalten.', category="error")
        return redirect(url_for('auth.signup'))

    if not Tools.email_check(input_email):
        flash('Ungültiges E-Mail-Format.', category="error")
        return redirect(url_for('auth.signup'))
        
    email_exists = User.query.filter_by(email=input_email).first()  # if this returns a user, then the email already exists in database
    if email_exists:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('E-Mail Adresse existiert bereits.', category="error")
        return redirect(url_for('auth.signup'))

    user_exists = User.query.filter_by(name=input_user).first()  # if this returns a user, then the email already exists in database
    if user_exists:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Benutzername existiert bereits.', category="error")
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    created_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # set location
    location = request.form.get('location').strip()
    if location:
        selected_location = Database.search(Locations, keyword=location, search_columns=[Locations.name], amount=1)
        if selected_location:
            location_id = selected_location.id
            location_name = selected_location.name
        else:
            location_id = 0
            location_name = ""
    else:
        location_id = 0
        location_name = ""


    new_user = User(email=input_email, 
                    name=input_user, 
                    password=scrypt.hash(input_password), 
                    created=created_date, 
                    role=0,
                    enable_notifications=1,
                    location_id=location_id,
                    location=location_name,
                    total_logins=0)

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    flash('Erfolgreich Benutzerkonto erstellt!', category="success")
    return redirect(url_for('auth.login'))

@auth.route('/ausloggen')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Du hast dich erfolgreich abgemeldet!', category="success")
    return redirect(url_for('main.index'))
