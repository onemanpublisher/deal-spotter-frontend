from flask import Blueprint, request, make_response, jsonify, redirect, flash, current_app
from . import db
from flask_login import login_required, current_user
from .tools import Database, Tools
from datetime import datetime, timezone
from .models import Watchlists, Comments, Comment_Upvotes, Ratings, Items, Notifications, Item_Recognition, Locations
from config import CATEGORY_PATH_WIN, CATEGORY_PATH_LIN
import platform
import logging
import requests
import os


methods = Blueprint('methods', __name__)

system = platform.system()
if system == "Linux":
    CATEGORY_PATH = CATEGORY_PATH_LIN
elif system == "Windows":
    CATEGORY_PATH = CATEGORY_PATH_WIN

@login_required
@methods.route('/set_category', methods=['POST'])
def handle_set_category():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    if current_user.role != 1:
        return jsonify({"message": "ERROR 404"})

    try:
        redirect_url = request.form.get('redirect_url')
        item_name = request.form.get('item_name')
        item_id = request.form.get('item_id')
        selected_category = request.form.get('selected_category')
        if not selected_category or not item_name:
            flash(f'Du musst eine Kategorie auswählen!', category="error")
            return redirect(redirect_url)
        Tools.append_and_save_to_file(CATEGORY_PATH, selected_category, item_name)
        filter_args = {
            "id": item_id,
            "name": item_name,
        }
        item_to_add_category = Database.search(Items, filter_args=filter_args, amount=1)
        item_to_add_category.category = selected_category
        item_to_add_category.sub_category = item_name
        db.session.add(item_to_add_category)
        db.session.commit()

        Database.delete_cache(Items, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Items, filter_args={'id': int(item_id)}, amount=1)

        print(f"set {item_name} to category {selected_category} in {CATEGORY_PATH} file")
        logging.info(f"set {item_name} to category {selected_category} in {CATEGORY_PATH} file")
        flash(f'Erfolgreich {item_name} zu der Kategorie {selected_category} hinzugefügt!', category="success")
    except:
        flash(f'Konnte nicht {item_name} zu der Kategorie {selected_category} hinzufügen!', category="error")
    return redirect(redirect_url)

@methods.route('/set_location', methods=['POST'])
def set_manually_location_post():
    location = request.form.get('location').strip()
    redirect_url = request.form.get('redirect_url')
    selected_location = None
    if location != "":
        selected_location = Database.search(Locations, keyword=location, search_columns=[Locations.id, Locations.name], amount=1)
    if selected_location:
        response = make_response(redirect(redirect_url))
        location_name = selected_location.name
        response.set_cookie('location', str(location_name), max_age=31536000, samesite='None', secure=True)  # 1 year
        response.set_cookie('location_id', str(selected_location.id), max_age=31536000, samesite='None', secure=True)  # 1 year
        if current_user.is_authenticated:  # set user location id
            current_user.location = location_name
            current_user.location_id = selected_location.id
            db.session.commit()
            Database.delete_cache(Items, filter_args={'user_id': int(current_user.id)})
        flash(f"Standort '{location_name}' erfolgreich ausgewählt!", category="success")
        return response
    else:
        flash(f'Standort konnte nicht ausgewählt werden!', category="error")
        return redirect(redirect_url)

@methods.route('/reset_location', methods=['POST'])
def reset_location_post():
    redirect_url = request.form.get('redirect_url')

    response = make_response(redirect(redirect_url))
    response.set_cookie('location', "", max_age=31536000, samesite='None', secure=True)  # 1 year
    response.set_cookie('location_id', str(0), max_age=31536000, samesite='None', secure=True)  # 1 year
    if current_user.is_authenticated:
        current_user.location = ""
        current_user.location_id = 0
        db.session.commit()
        Database.delete_cache(Items, filter_args={'user_id': int(current_user.id)})
    flash(f"Standort erfolgreich zurückgesetzt!", category="success")
    return response

@methods.route('/set_auto_location', methods=['POST'])
def set_automatically_location_post():
    try:
        redirect_url = request.form.get('redirect_url')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if latitude and longitude:
            # Use OpenStreetMap Nominatim API to get city name from latitude and longitude
            api_url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&addressdetails=1'
            response = requests.get(api_url)
            result = response.json()
            # Extract city name from the result
            address = result.get('address')
            if address:
                town = address.get('town')
                county = address.get('county')
                city = address.get('city')
                l_locations = [value for value in [town, county, city] if value is not None]
            all_locations = Database.search(Locations)

            for location in all_locations:
                location_name = location.name
                if any(location_name in value for value in l_locations):
                    response = make_response(redirect(redirect_url))
                    response.set_cookie('location', str(location.name), max_age=31536000, samesite='None', secure=True)  # 1 year
                    response.set_cookie('location_id', str(location.id), max_age=31536000, samesite='None', secure=True)  # 1 year
                    if current_user.is_authenticated:  # set user location id
                        current_user.location_id = location.id
                        current_user.location = location_name
                        db.session.commit()
                        Database.delete_cache(Items, filter_args={'user_id': int(current_user.id)})
                    flash(f"Standort '{location_name}' erfolgreich ausgewählt!", category="success")
                    return response
            else:
                logging.error("Standort konnte nicht erfasst werden!")
                print("Standort konnte nicht erfasst werden!")
                flash(f"Standort konnte nicht erfasst werden!", category="error")
        else:
            logging.error("Standortdaten konnte nicht erfasst werden!")
            flash(f"Standortdaten konnte nicht erfasst werden!", category="error")
            return redirect(redirect_url)
    except Exception as e:
        print(str(e))
        logging.error(str(e))
        flash(f"Standortdaten konnte nicht erfasst werden! Versuche es später erneut!", category="error")
        return redirect(redirect_url)

@login_required
@methods.route('/set_keyword_notification', methods=['POST'])
def notification_keyword_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    keyword = request.form.get('keyword').strip()
    redirect_url = request.form.get('redirect_url')
    filter_args = {
        "user_id": current_user.id
    }
    user_notifications = Database.search(Notifications, filter_args=filter_args)

    if not keyword:
        flash('Gebe ein Stichwort ein!', category="error")
    elif keyword in [user_notification.name for user_notification in user_notifications]: 
        flash(f'Ein Element mit dem gleichen Namen {keyword} existiert bereits!', category="error")
    else:
        try:
            if current_user.enable_notifications: enabled = 1
            else: enabled = 0
            new_notification = Notifications(
                user_id=current_user.id,
                name=keyword,
                enabled=enabled,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            db.session.add(new_notification)
            db.session.commit()
            flash('Dein Stichwort wurde erfolgreich erstellt!', category="success")

            Database.delete_cache(Notifications, filter_args={'user_id': int(current_user.id)})
        except:
            flash('Dein Stichwort konnte nicht erstellt werden!', category="error")

    return redirect(redirect_url)

@login_required
@methods.route('/set_settings', methods=['POST'])
def handle_settings():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    redirect_url = request.form.get('redirect_url')
    checkbox_value = request.form.get('state')
    check_box_state = 1 if checkbox_value == 'on' else 0

    filter_args = {
        "user_id": current_user.id,
    }

    with current_app.app_context():  # using this to flush 2 commits on different accesses (one with current_user and the second with Database.x)
        if check_box_state:
            current_user.enable_notifications = 1
            db.session.commit()  # Commit changes to current_user
            for user_notification in Database.search(Notifications, filter_args=filter_args):
                user_notification.enabled = 1
                db.session.add(user_notification)
            flash(f"Du wirst nun per E-Mail benachrichtigt, sobald eines deiner Angebote in der Einkaufsliste wieder verfügbar ist.", category="success")
        else:
            current_user.enable_notifications = 0
            db.session.commit()  # Commit changes to current_user
            for user_notification in Database.search(Notifications, filter_args=filter_args):
                user_notification.enabled = 0
                db.session.add(user_notification)
            flash(f"Du erhältst keine E-Mail-Benachrichtigungen zu deiner Einkaufsliste mehr.", category="info")

        db.session.commit()

    Database.delete_cache(Notifications, filter_args={'user_id': int(current_user.id)})
    return redirect(redirect_url)

@login_required
@methods.route('/set_notification_state', methods=['POST'])
def handle_overwrite_notification_state():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition_id')
    name = request.form.get('name')
    checkbox_value = request.form.get('state')
    check_box_state = 1 if checkbox_value == 'on' else 0

    filter_args = {
        "user_id": current_user.id,
    }
    if recognition_id is not None and recognition_id != "None":
        filter_args["recognition_id"] = recognition_id  # use recognition_id as identifier if doesnt exists do it with the name
    else:
        filter_args["name"] = name

    notification_to_overwrite = Database.search(Notifications, filter_args=filter_args, amount=1)
    if notification_to_overwrite:
        if check_box_state:
            notification_to_overwrite.enabled = 1
            flash(f"Du wirst per E-Mail benachrichtigt, sobald das Angebot '{notification_to_overwrite.name}' wieder verfügbar ist.", category="success")
        else:
            notification_to_overwrite.enabled = 0
            flash(f"Du wirst nicht mehr per E-Mail über das Angebot '{notification_to_overwrite.name}' benachrichtigt.", category="info")

        db.session.add(notification_to_overwrite)
        db.session.commit()
        Database.delete_cache(Notifications, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Notifications, filter_args={'user_id': int(current_user.id)})
    else:
        flash(f"'{name}' zu ändern hat nicht funktioniert, versuchen es später noch einmal!", category="error")

    return redirect(redirect_url)

@login_required
@methods.route('/remove_notification', methods=['POST'])
def handle_remove_notification():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition_id')
    name = request.form.get('name')
    
    filter_args = {
        "user_id": current_user.id,
    }
    if recognition_id is not None and recognition_id != "None":
        filter_args["recognition_id"] = recognition_id  # use recognition_id as identifier if doesnt exists do it with the name
    else:
        filter_args["name"] = name

    watchlist_to_delete = Database.search(Notifications, filter_args=filter_args, amount=1)
    if watchlist_to_delete:
        db.session.delete(watchlist_to_delete)
        db.session.commit()
        flash(f"Erfolgreich '{name}' aus deinen Benachrichtigungen entfernt!", category="success")
        Database.delete_cache(Notifications, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Notifications, filter_args={'user_id': int(current_user.id)})
    else:
        flash(f"'{name}' zu löschen hat nicht funktioniert, versuchen es später noch einmal!", category="error")

    return redirect(redirect_url)

@login_required
@methods.route('/remove_watchlist', methods=['POST'])
def handle_remove_watchlist():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition_id')
    item_name = request.form.get('item_name')
    
    filter_args = {
        "user_id": current_user.id,
        "recognition_id": recognition_id
    }

    watchlist_to_delete = Database.search(Watchlists, filter_args=filter_args, amount=1)
    if watchlist_to_delete:
        db.session.delete(watchlist_to_delete)
        db.session.commit()
        flash(f"Erfolgreich '{item_name}' aus deiner Einkaufsliste gelöscht!", category="success")
    else:
        flash(f"'{item_name}' zu löschen hat nicht funktioniert, versuchen es später noch einmal!", category="error")

    Database.delete_cache(Watchlists, filter_args=filter_args, amount=1)  # cache used above
    Database.delete_cache(Watchlists, filter_args={'user_id': int(current_user.id)})
    return redirect(redirect_url)

@login_required
@methods.route('/handle_watchlist', methods=['POST'])
def handle_watchlist_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    redirect_url = request.form.get('redirect_url')
    item_id = request.form.get('item_id')
    filter_args = {
        "id": item_id
    }
    item = Database.search(Items, filter_args=filter_args, amount=1)  # get the item with the item_id
    if item:
        filter_args = {
            "user_id": current_user.id,
            "prospect_id": item.prospect_id,
            "recognition_id": item.recognition_id,
            "item_id": item_id
        }
        already_exists = Database.search(Watchlists, filter_args=filter_args, amount=1)
        if not already_exists:
            new_watchlist = Watchlists(
                user_id=current_user.id, 
                name=item.name,
                market=item.market,
                category=item.category,
                sub_category=item.sub_category,
                recognition_id=item.recognition_id,
                item_id=item_id,
                prospect_id=item.prospect_id,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            db.session.add(new_watchlist)
            db.session.commit()
            flash(f"Erfolgreich '{item.name}'' zu deiner Einkaufsliste hinzugefügt!", category="success")
        else:
            try:
                db.session.delete(already_exists)
                db.session.commit()
                flash(f"Erfolgreich '{item.name}' aus deiner Einkaufsliste entfernt!", category="success")
            except Exception as e:
                flash('Es ist ein Fehler aufgetreten, versuche es später erneut!', category="error")
                logging.error(f"handle_watchlist_post: {e}")
    else:
        flash('Es ist ein Fehler aufgetreten, versuche es später erneut!', category="error")

    Database.delete_cache(Watchlists, filter_args=filter_args, amount=1)  # cache used above
    Database.delete_cache(Watchlists, filter_args={'user_id': int(current_user.id)})
    Database.delete_cache(Watchlists, filter_args={"user_id": int(current_user.id), "prospect_id": int(item.prospect_id), "recognition_id": int(item.recognition_id), "item_id": int(item_id)})

    return redirect(redirect_url)

@login_required
@methods.route('/handle_notification', methods=['POST'])
def handle_notification_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 


    redirect_url = request.form.get('redirect_url')
    item_id = request.form.get('item_id')
    filter_args = {
        "id": item_id
    }
    item = Database.search(Items, filter_args=filter_args, amount=1)  # get the item with the item_id
    if item:
        filter_args = {
            "user_id": current_user.id,
            "prospect_id": item.prospect_id,
            "recognition_id": item.recognition_id,
            "item_id": item_id
        }
        already_exists = Database.search(Notifications, filter_args=filter_args, amount=1)
        if not already_exists:
            if current_user.enable_notifications: enabled = 1
            else: enabled = 0
            new_notification = Notifications(
                user_id=current_user.id, 
                name=item.name,
                category=item.category,
                sub_category=item.sub_category,
                market=item.market,
                prospect_id=item.prospect_id,
                recognition_id=item.recognition_id,
                item_id=item_id,
                enabled=enabled,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            db.session.add(new_notification)
            db.session.commit()
            flash(f"Erfolgreich '{item.name}'' zu deinen Benachrichtigungen hinzugefügt!", category="success")
        else:
            try:
                db.session.delete(already_exists)
                db.session.commit()
                flash(f"Erfolgreich '{item.name}' aus deinen Benachrichtigungen entfernt!", category="success")
            except Exception as e:
                flash('Es ist ein Fehler aufgetreten, versuche es später erneut!', category="error")
                logging.error(f"handle_watchlist_post: {e}")
    else:
        flash('Es ist ein Fehler aufgetreten, versuche es später erneut!', category="error")
    
    Database.delete_cache(Notifications, filter_args=filter_args, amount=1)  # cache used above
    Database.delete_cache(Notifications, filter_args={'user_id': int(current_user.id)})
    Database.delete_cache(Notifications, filter_args={"user_id": int(current_user.id), "prospect_id": int(item.prospect_id), "recognition_id": int(item.recognition_id), "item_id": int(item_id)})

    return redirect(redirect_url)

@login_required
@methods.route('/set_comment', methods=['POST'])
def comment_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    comment_body = request.form.get('comment_body')
    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition')
    if len(comment_body) <= 15:
        flash('Dein Kommentar muss mindestens 15 Zeichen lang sein!', category="error")
    else:
        filtered_comment = Tools.filter_profanity(comment_body)
        try:
            new_comment = Comments(
                user_id=current_user.id,
                user_name=current_user.name,
                recognition_id=recognition_id,
                text=filtered_comment,
                upvotes=0,
                visible=1,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            db.session.add(new_comment)
            db.session.commit()
            flash('Dein Kommentar wurde erfolgreich erstellt!', category="success")

            Database.delete_cache(Comments, filter_args={'recognition_id': int(recognition_id)}, sort_by_datetime=True)
        except:
            flash('Dein Kommentar konnte nicht erstellt werden!', category="error")
    return redirect(redirect_url)

@login_required
@methods.route('/set_comment_upvote', methods=['POST'])
def handle_comment_upvote():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    data = request.get_json()
    comment_id = data.get('comment_id')
    recognition_id = data.get('recognition_id')

    filter_args = {
        "user_id": current_user.id,
        "comment_id": comment_id,
    }
    already_exists = Database.search(Comment_Upvotes, filter_args=filter_args, amount=1)
    if not already_exists:
        new_comment_upvote = Comment_Upvotes(
            user_id=current_user.id, 
            comment_id=comment_id,
            datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        db.session.add(new_comment_upvote)
        db.session.commit()
        
        filter_args = {
            "id": comment_id,
        }
        comment_entry = Database.search(Comments, filter_args=filter_args, amount=1)
        comment_entry.upvotes = (comment_entry.upvotes or 0) + 1
        db.session.add(comment_entry)  # working just like update()
        db.session.commit()

        Database.delete_cache(Comment_Upvotes, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Comments, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Comment_Upvotes, filter_args={'user_id': int(current_user.id)})
        Database.delete_cache(Comments, filter_args={'recognition_id': int(recognition_id)}, sort_by_datetime=True)

    return jsonify({"message": "Element added to the list"})

@login_required
@methods.route('/set_comment_remove', methods=['POST'])
def comment_remove_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    comment_id = request.form.get('comment_id')
    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition_id')

    filter_args = {
        "id": comment_id,
        "user_id": current_user.id
    }
    comment_to_remove = Database.search(Comments, filter_args=filter_args, amount=1)
    if comment_to_remove:
        db.session.delete(comment_to_remove)
        db.session.commit()

        filter_args = {
            "comment_id": comment_id
        }
        comment_likes_to_remove = Database.search(Comment_Upvotes, filter_args=filter_args)
        if comment_likes_to_remove:
            for comment_like_to_remove in comment_likes_to_remove:
                db.session.delete(comment_like_to_remove)
            db.session.commit()

        Database.delete_cache(Comments, filter_args=filter_args, amount=1)  # cache used above
        Database.delete_cache(Comment_Upvotes, filter_args=filter_args)  # cache used above
        Database.delete_cache(Comments, filter_args={'recognition_id': int(recognition_id)}, sort_by_datetime=True)
        Database.delete_cache(Comment_Upvotes, filter_args={'user_id': int(current_user.id)})
        
        flash('Dein Kommentar wurde erfolgreich entfernt!', category="success")
    else:
        flash('Dein Kommentar konnte nicht entfernt werden!', category="error")

    return redirect(redirect_url)

@login_required
@methods.route('/set_rating', methods=['POST'])
def rating_post():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    rating = request.form.get('rating', type=int)
    redirect_url = request.form.get('redirect_url')
    recognition_id = request.form.get('recognition')

    if rating in [1, 2, 3, 4, 5]:
        filter_args = {
            "user_id": current_user.id,
            "recognition_id": recognition_id
        }
        already_exists = Database.search(Ratings, filter_args=filter_args, amount=1)
        if already_exists:
            already_exists.rating = rating
            already_exists.datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            db.session.add(already_exists)
        else:
            new_rating = Ratings(
                recognition_id=recognition_id,
                user_id=current_user.id,
                rating=rating,
                datetime=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            db.session.add(new_rating)
        db.session.commit()

        Database.delete_cache(Ratings, filter_args={'recognition_id': int(recognition_id)})
        Database.delete_cache(Ratings, filter_args=filter_args, amount=1)
        Database.delete_cache(Ratings)
        flash('Deine Bewertung wurde erfolgreich erstellt!', category="success")
    else:
        flash('Deine Bewertung konnte nicht erstellt werden!', category="error")
    return redirect(redirect_url)

@methods.route('/set_cookie', methods=['POST'])
def set_cookie():
    response = make_response(jsonify({'status': 'ok'}))  # Return JSON response
    # response = make_response(render_template('cookie_consent.html'))
    if request.form.get('choice') == 'accept':
        response.set_cookie('consent', 'accepted', max_age=31536000, samesite='None', secure=True)  # 1 year
    else:
        response.set_cookie('consent', 'declined', max_age=31536000, samesite='None', secure=True)  # 1 year
    return response

@login_required
@methods.route("/suggestion_keyword")
def suggestion_keyword():
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    search = request.args.get('query')
    suggestion_keywords_items = Database.search(Item_Recognition, keyword=search, search_columns=[Item_Recognition.name], amount=10)
    suggestion_keywords = [keyword.name for keyword in suggestion_keywords_items]
    return jsonify({"suggestions":suggestion_keywords})

@methods.route("/suggestion_items")
def suggestion_items():
    search = request.args.get('query')
    suggestion_keywords_items = Database.search(Items, keyword=search, search_columns=[Items.name], amount=10)
    suggestion_keywords = [keyword.name for keyword in suggestion_keywords_items]
    suggestion_keywords = list(set(suggestion_keywords))  # delete duplicates
    return jsonify({"suggestions":suggestion_keywords})

@methods.route("/suggestion_locations")
def suggestion_locations():
    search = request.args.get('query')
    suggestion_keywords_locations = Database.search(Locations, keyword=search, search_columns=[Locations.name])
    suggestion_keywords = [keyword.name for keyword in suggestion_keywords_locations]
    return jsonify({"suggestions":suggestion_keywords})

@login_required
@methods.route('/clear_cache', methods=['POST'])
def clear_cache():
    redirect_url = request.form.get('redirect_url')
    if not current_user.is_authenticated:
        return jsonify({"message": "dont even try"}) 

    if current_user.role == 1:
        try:
            cmd = "redis-cli flushall"
            exit_code  = os.system(cmd)
            flash(f'Cache erfolgreich gelöscht! exit_code: {exit_code}', category="success")
        except:
            flash('Fehler!', category="error")
    return redirect(redirect_url)
