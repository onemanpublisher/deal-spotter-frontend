from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
	__tablename__ = 'user'
	id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
	name = db.Column(db.String(200))
	email = db.Column(db.String(100), unique=True)
	password = db.Column(db.String(100))
	created = db.Column(db.String(100))
	last_login = db.Column(db.String(100))
	role = db.Column(db.Integer)
	total_logins = db.Column(db.Integer)
	enable_notifications = db.Column(db.Integer)
	location = db.Column(db.String(100))
	location_id = db.Column(db.Integer)

class Watchlists(db.Model):
    __tablename__ = 'watchlists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    market = db.Column(db.String(200))
    category = db.Column(db.String(200))
    sub_category = db.Column(db.String(200))
    recognition_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    item_id = db.Column(db.Integer)
    prospect_id = db.Column(db.Integer)
    datetime = db.Column(db.String(100))

class Prospects(db.Model):
	__tablename__ = 'prospects'
	id = db.Column(db.Integer, primary_key=True)
	prospect_id = db.Column(db.Integer)
	name = db.Column(db.String(1000))
	url = db.Column(db.String(200))
	thumbnail = db.Column(db.String(200))
	thumbnail_resized = db.Column(db.String(200))
	thumbnail_2_resized = db.Column(db.String(200))
	pages = db.Column(db.Integer)
	offers = db.Column(db.Integer)
	actions = db.Column(db.Integer)
	period_start = db.Column(db.String(100))
	period_end = db.Column(db.String(100))
	market = db.Column(db.String(200))
	generated_items = db.Column(db.Integer)
	processed_pages = db.Column(db.Integer)
	processed_items = db.Column(db.Integer)
	expired = db.Column(db.Integer)
	location_id = db.Column(db.Integer)
	datetime = db.Column(db.String(100))
 
class Prospect_Pages(db.Model):
    __tablename__ = 'prospect_pages'
    id = db.Column(db.Integer, primary_key=True)
    prospect_id = db.Column(db.Integer)
    file_path = db.Column(db.String(200))
    file_path_rel = db.Column(db.String(200))
    file_path_rel_resized = db.Column(db.String(200))
    page_num = db.Column(db.Integer)
    url = db.Column(db.String(200))
    datetime = db.Column(db.String(100))
    
class Items(db.Model):
	__tablename__ = 'items'
	id = db.Column(db.Integer, primary_key=True)
	prospect_id = db.Column(db.Integer)
	recognition_id = db.Column(db.Integer)
	location_id = db.Column(db.Integer)
	prospect_page_num = db.Column(db.Integer)
	name = db.Column(db.String(200))
	price = db.Column(db.String(100))
	discount = db.Column(db.String(100))
	reference_image = db.Column(db.String(200))
	original_image = db.Column(db.String(200))
	original_image_rel = db.Column(db.String(200))
	original_image_rel_resized = db.Column(db.String(200))
	market = db.Column(db.String(200))
	sub_category = db.Column(db.String(200))
	category = db.Column(db.String(200))
	hashtags = db.Column(db.String(200))
	datetime = db.Column(db.String(100))

class Item_Recognition(db.Model):
	__tablename__ = 'item_recognition'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(200))
	market = db.Column(db.String(200))
	datetime = db.Column(db.String(100))
 
class Ratings(db.Model):
	__tablename__ = 'ratings'
	id = db.Column(db.Integer, primary_key=True)
	recognition_id = db.Column(db.Integer)
	user_id = db.Column(db.Integer)
	rating = db.Column(db.Integer)
	datetime = db.Column(db.String(100))

class Comments(db.Model):
	__tablename__ = 'comments'
	id = db.Column(db.Integer, primary_key=True)
	recognition_id = db.Column(db.Integer)
	user_id = db.Column(db.Integer)
	user_name = db.Column(db.String(200))
	text = db.Column(db.String(500))
	upvotes = db.Column(db.Integer)
	visible = db.Column(db.Integer)
	datetime = db.Column(db.String(100))

class Comment_Upvotes(db.Model):
	__tablename__ = 'comment_upvotes'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer)
	comment_id = db.Column(db.Integer)
	datetime = db.Column(db.String(100))

class Notifications(db.Model):
	__tablename__ = 'notifications'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer)
	name = db.Column(db.String(200))
	category = db.Column(db.String(200))
	sub_category = db.Column(db.String(200))
	market = db.Column(db.String(200))
	prospect_id = db.Column(db.Integer)
	recognition_id = db.Column(db.Integer)
	item_id = db.Column(db.Integer)
	enabled = db.Column(db.Integer)
	datetime = db.Column(db.String(100))

class Locations(db.Model):
	__tablename__ = 'locations'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(200))
