from flask import Blueprint, render_template, request, redirect, url_for, Response
from flask_login import login_required, current_user
from .tools import Database, Tools
import platform
from datetime import datetime
from collections import defaultdict
from .models import Watchlists, Prospects, Items, Prospect_Pages, Comments, Comment_Upvotes, Ratings, Notifications
import re

# sys.path.append("G:\10. Programmierung\6. Python OneManPublisher\Deal_Spotter")
# from scripts.utils.omp_tools import OsTools

main = Blueprint('main', __name__)
system = platform.system()

@main.route('/')
def index():
    filter_args = Tools.load_locations_filter_args()
    prospects = Database.search(Prospects, filter_args=filter_args, random_order=True)

    total_prospects = len(prospects)
    prospects = prospects[:12]

    filter_args = Tools.load_locations_filter_args()
    items = Database.search(Items, filter_args=filter_args, random_order=True)

    total_items = len(items)
    items = items[:12]  # display only 12 items

    similar_items_ratings = Database.search(Ratings)  # get all ratings
    ratings_dict = {}
    for similar_rating in similar_items_ratings:
        if similar_rating.recognition_id not in ratings_dict:
            ratings_dict[similar_rating.recognition_id] = {
                'ratings_sum': similar_rating.rating,
                'count': 1
            }
        else:
            ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
            ratings_dict[similar_rating.recognition_id]['count'] += 1

    for item in items:
        rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
        item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
        item.amount_ratings = rating_data['count']

    return render_template('index.html', prospects=prospects, total_prospects=total_prospects, total_items=total_items, items=items, datetime=datetime)

@main.route('/markt')
def markets():
    return render_template('markets.html')

@main.route('/markt/<string:name>')
def market(name):
    current_items = None
    page = None
    total_items = None
    start_index = None
    per_page = 28  # Number of items per page
    market = name

    filter_args = {
        "market": name
    }
    filter_args = Tools.load_locations_filter_args(filter_args)
    items = Database.search(Items, filter_args=filter_args, random_order=True)

    if items:
        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_items = items[start_index:end_index]  # Get the items for the current page
        total_items = len(items)
        
        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for current_item in current_items:
            rating_data = ratings_dict.get(current_item.recognition_id, {'ratings_sum': 0, 'count': 0})
            current_item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            current_item.amount_ratings = rating_data['count']

    return render_template('market.html', market=market, items=current_items, page=page, total_items=total_items, per_page=per_page, start_index=start_index)

@main.route('/benachrichtigungen', methods=['GET'])
@login_required
def notification():
    if not current_user.is_authenticated:
        return redirect(url_for('main.index'))

    current_notification = None
    page = None
    total_notifications = None
    start_index = None
    per_page = 20  # Number of items per page

    filter_args = {
        "user_id": current_user.id,
    }
    notification_items = Database.search(Notifications, filter_args=filter_args)
    notification_items_basic = []
    notification_items_small = []
    where_conditions = defaultdict(str)

    if notification_items:
        for i, notification in enumerate(notification_items):
            if notification.recognition_id:
                where_conditions[i] = notification.recognition_id
            else:
                notification_items_small.append(notification)

        if where_conditions:
            where_conditions["where"] = "recognition_id"  # assign where statement
            filter_args = {
                "location_id": current_user.location_id
            }
            notification_items_basic = Database.search(Items, filter_args=filter_args, where_conditions=where_conditions)

        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_notification = notification_items_basic[start_index:end_index]  # Get the items for the current page
        total_notifications = int(len(notification_items_basic))

        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for item in notification_items_basic:
            rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
            item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            item.amount_ratings = rating_data['count']

    return render_template('notifications.html', id=current_user.id, notifications=current_notification, notification_items_basic=notification_items_basic, notification_items_small=notification_items_small, page=page, total_notifications=total_notifications, per_page=per_page, start_index=start_index)

@main.route('/merkliste', methods=['GET'])
@login_required
def watchlist():
    if current_user.is_authenticated:
        current_watchlist = None
        page = None
        total_watchlist = None
        start_index = None
        items_not_currently_available = None
        items = []
        per_page = 20  # Number of items per page

        filter_args = {
            "user_id": current_user.id,
        }
        watchlist_elements = Database.search(Watchlists, filter_args=filter_args)

        if watchlist_elements:
            item_ids = [watchlist.item_id for watchlist in watchlist_elements]
            filter_args = Tools.load_locations_filter_args()
            all_items = Database.search(Items, filter_args=filter_args)

            items_not_currently_available = []
            for item in all_items:
                if int(item.id) in item_ids:
                    items.append(item)            

            # get items which are not currently available
            items_still_existing = [int(item.id) for item in items]
            items_ids_not_currently_available = [item_id for item_id in item_ids if item_id not in items_still_existing]
            for watchlist in watchlist_elements:
                if int(watchlist.item_id) in items_ids_not_currently_available:
                    items_not_currently_available.append(watchlist)

            page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
            # Calculate the start and end indices for the current page
            start_index = (page - 1) * per_page
            end_index = start_index + per_page
            current_watchlist = items[start_index:end_index]  # Get the items for the current page
            total_watchlist = int(len(items))
            
            similar_items_ratings = Database.search(Ratings)  # get all ratings
            ratings_dict = {}
            for similar_rating in similar_items_ratings:
                if similar_rating.recognition_id not in ratings_dict:
                    ratings_dict[similar_rating.recognition_id] = {
                        'ratings_sum': similar_rating.rating,
                        'count': 1
                    }
                else:
                    ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                    ratings_dict[similar_rating.recognition_id]['count'] += 1

            for item in items:
                rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
                item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
                item.amount_ratings = rating_data['count']
            
        return render_template('watchlist.html', id=current_user.id, items_not_currently_available=items_not_currently_available, watchlist=current_watchlist, page=page, total_watchlist=total_watchlist, per_page=per_page, start_index=start_index)
    else:
        return redirect(url_for('main.index'))

@main.route('/datenschutz')
def data_privacy():
    return render_template('data_privacy.html')

@main.route('/suche', methods=['GET'])
def search():
    current_items = None
    page = None
    total_items = None
    start_index = None
    per_page = 28  # Number of items per page

    search = request.args.get('search', default="", type=str)
    if search:
        search = search.strip()  # remove spacing from start and end of the string

    filter_args = Tools.load_locations_filter_args()
    items = Database.search(Items, filter_args=filter_args, keyword=search, search_columns=[Items.name, Items.category, Items.market])
    if items:
        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_items = items[start_index:end_index]  # Get the items for the current page
        total_items = len(items)
        
        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for item in items:
            rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
            item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            item.amount_ratings = rating_data['count']
    return render_template('search.html', keyword=search, items=current_items, page=page, total_items=total_items, per_page=per_page, start_index=start_index)

@main.route('/angebote', methods=['GET'])
def items():
    current_items = None
    page = None
    total_items = None
    start_index = None
    per_page = 28  # Number of items per page
    sub_categories = []

    selected_market = None
    selected_category = None
    selected_sub_category = None

    selected_market = request.args.get('market', default=None, type=str)  # Get the 'page' parameter from the URL
    selected_category = request.args.get('category', default=None, type=str)
    selected_sub_category = request.args.get('sub_category', default=None, type=str)
    
    filter_args = Tools.load_locations_filter_args()
    items = Tools.fetch_categorised_items(selected_market, selected_category, selected_sub_category, filter_args)
    if items:
        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_items = items[start_index:end_index]  # Get the items for the current page
        total_items = len(items)
        
        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for item in items:
            rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
            item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            item.amount_ratings = rating_data['count']

        sub_categories = Tools.load_sub_categories_keys(selected_category, selected_market)

    return render_template('items.html', items=current_items, page=page, total_items=total_items, per_page=per_page, start_index=start_index, selected_market=selected_market, selected_category=selected_category, selected_sub_category=selected_sub_category, sub_categories=sub_categories)

@main.route('/kategorien')
def categories():
    return render_template('categories.html')

@main.route('/kategorien/<string:name>')
def category(name):
    current_items = None
    page = None
    total_items = None
    start_index = None
    per_page = 28  # Number of items per page

    if name == "Ohne Kategorie":
        filter_args = {"category": ""}
        keyword = ""  #! resets the name for the query
    elif name == "Alle Kategorien":
        filter_args = defaultdict(str)
        keyword = ""
    else:
        filter_args = defaultdict(str)  # assign empty dict
        keyword = name

    selected_market = request.args.get('market', default="Alle Märkte", type=str)  # Get the 'page' parameter from the URL
    if type(selected_market) == str and selected_market != "Alle Märkte":
        filter_args["market"] = selected_market

    filter_args = Tools.load_locations_filter_args(filter_args)
    items = Database.search(Items, filter_args=filter_args, keyword=keyword)
    if items:
        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_items = items[start_index:end_index]  # Get the items for the current page
        total_items = len(items)
        
        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for current_item in current_items:
            rating_data = ratings_dict.get(current_item.recognition_id, {'ratings_sum': 0, 'count': 0})
            current_item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            current_item.amount_ratings = rating_data['count']
                
    return render_template('category.html', category=name, selected_market=selected_market, items=current_items, page=page, total_items=total_items, per_page=per_page, start_index=start_index)

@main.route('/angebote/<int:item_id>')
def get_item_content(item_id):
    item = None
    prospect = None
    similar_items = None
    total_similar_items = None
    watchlist_exists = None
    notification_exists = None
    comments = None
    total_comments = None
    current_comments = None
    comment_upvotes = None
    logged_in = False
    customer_id = None
    if current_user.is_authenticated:
        admin = current_user.role
    else:
        admin = None
    page = None
    start_index = None
    comments_per_page = 6  # Number of items per page | comments
    
    rating = None
    item_rating = 0
    total_ratings = 0

    filter_args = {
        "id": item_id
    }
    # filter_args = Tools.load_locations_filter_args(filter_args)
    item = Database.search(Items, filter_args=filter_args, amount=1)
    if item:
        filter_args = {
            "prospect_id": item.prospect_id
        }
        # filter_args = Tools.load_locations_filter_args(filter_args)
        prospect = Database.search(Prospects, filter_args=filter_args, amount=1)

        if current_user.is_authenticated:
            filter_args = {
                "user_id":current_user.id, 
                "prospect_id": item.prospect_id,
                "recognition_id": item.recognition_id,
                "item_id":item_id
            }
            # watchlist_exists = Database.search(Watchlists, amount=1, filter_args=filter_args)
            # notification_exists = Database.search(Notifications, amount=1, filter_args=filter_args)
            watchlist_exists = Database.search(Watchlists, filter_args=filter_args)
            notification_exists = Database.search(Notifications, filter_args=filter_args)

        if item.category != "None":
            item_category = item.category.split(",")[0].strip()  # select only the first category
            # filter_args = {
            #     "category": item_category,
            # }
            # similar_items = Database.search(Items, filter_args=filter_args, keyword=item_category, random_order=True)  #! new idea. but not 100% perfect, maybe create another page for keyword adding
            filter_args = Tools.load_locations_filter_args()
            similar_items = Database.search(Items, filter_args=filter_args, keyword=item_category, random_order=True)

            total_similar_items = len(similar_items)
            similar_items = [item for item in similar_items if item.id != item_id]  # delete current item so its not displayed on similar table
            similar_items = similar_items[:12]

            similar_items_ratings = Database.search(Ratings)  # get all ratings
            ratings_dict = {}
            for similar_rating in similar_items_ratings:
                if similar_rating.recognition_id not in ratings_dict:
                    ratings_dict[similar_rating.recognition_id] = {
                        'ratings_sum': similar_rating.rating,
                        'count': 1
                    }
                else:
                    ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                    ratings_dict[similar_rating.recognition_id]['count'] += 1

            for similar_item in similar_items:
                rating_data = ratings_dict.get(similar_item.recognition_id, {'ratings_sum': 0, 'count': 0})
                similar_item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
                similar_item.amount_ratings = rating_data['count']

        filter_args = {
            "recognition_id": item.recognition_id
        }
        comments = Database.search(Comments, filter_args=filter_args, sort_by_datetime=True)

        total_comments = len(comments)
        if comments:
            page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
            # Calculate the start and end indices for the current page
            start_index = (page - 1) * comments_per_page
            end_index = start_index + comments_per_page
            current_comments = comments[start_index:end_index]  # Get the items for the current page

        filter_args = {
            "recognition_id": item.recognition_id
        }
        ratings = Database.search(Ratings, filter_args=filter_args)
        if ratings:
            total_rating = sum(rating.rating for rating in ratings)
            item_rating = round(total_rating / len(ratings), 1) if len(ratings) > 0 else 0
            total_ratings = len(ratings)

        if current_user.is_authenticated:  # used for comment like | if not logged it, it wont be possible to like comments
            filter_args = {
                "user_id": current_user.id
            }
            comment_upvotes = Database.search(Comment_Upvotes, filter_args=filter_args)
            logged_in = True
            customer_id = current_user.id
            
            for r in ratings:
                if current_user.id == r.user_id:
                    rating = r
                    break

    return render_template('item.html', 
                           item=item, 
                           similar_items=similar_items, 
                           total_similar_items=total_similar_items, 
                           prospect=prospect, 
                           datetime=datetime, 
                           watchlist_exists=watchlist_exists,
                           notification_exists=notification_exists,
                           total_comments=total_comments, 
                           comment_upvotes=comment_upvotes, 
                           logged_in=logged_in,
                           customer_id=customer_id,
                           comments=current_comments, 
                           page=page, 
                           comments_per_page=comments_per_page, 
                           start_index=start_index,
                           item_rating=item_rating,
                           rating=rating,
                           admin=admin,
                           total_ratings=total_ratings)

@main.route('/prospekte')
def prospects():
    selected_market = request.args.get('market', default="Alle Märkte", type=str)  # Get the 'page' parameter from the URL
    filter_args = defaultdict(str)
    if type(selected_market) == str and selected_market != "Alle Märkte":
        filter_args = {
            "name": selected_market
        }
    filter_args = Tools.load_locations_filter_args(filter_args)
    prospects = Database.search(Prospects, filter_args=filter_args)

    grouped_prospects = defaultdict(list)
    if prospects:
        sorted_prospects = sorted(prospects, key=lambda x: x.name)
        for prospect in sorted_prospects:
            grouped_prospects[prospect.name].append(prospect)

    total_length = sum(len(value_list) for value_list in grouped_prospects.values())
    return render_template('prospects.html', total_prospects=total_length, selected_market=selected_market, grouped_prospects=grouped_prospects, datetime=datetime)

@main.route('/prospekt-angebote/<int:prospect_id>', methods=['GET'])
def prospect_items(prospect_id):
    current_items = None
    page = None
    total_items = None
    start_index = None
    prospect = None
    per_page = 28  # Number of items per page

    filter_args = {
        "prospect_id": prospect_id,
    }
    filter_args = Tools.load_locations_filter_args(filter_args)
    prospect_items = Database.search(Items, filter_args=filter_args)
    if prospect_items:
        prospect = Database.search(Prospects, amount=1, filter_args=filter_args)

        page = request.args.get('page', default=1, type=int)  # Get the 'page' parameter from the URL
        # Calculate the start and end indices for the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        current_items = prospect_items[start_index:end_index]  # Get the items for the current page
        total_items = len(prospect_items)

        similar_items_ratings = Database.search(Ratings)  # get all ratings
        ratings_dict = {}
        for similar_rating in similar_items_ratings:
            if similar_rating.recognition_id not in ratings_dict:
                ratings_dict[similar_rating.recognition_id] = {
                    'ratings_sum': similar_rating.rating,
                    'count': 1
                }
            else:
                ratings_dict[similar_rating.recognition_id]['ratings_sum'] += similar_rating.rating
                ratings_dict[similar_rating.recognition_id]['count'] += 1

        for item in prospect_items:
            rating_data = ratings_dict.get(item.recognition_id, {'ratings_sum': 0, 'count': 0})
            item.rating = rating_data['ratings_sum'] / rating_data['count'] if rating_data['count'] > 0 else 0
            item.amount_ratings = rating_data['count']

    return render_template('prospect_items.html', prospect_items=current_items, prospect=prospect, page=page, total_items=total_items, per_page=per_page, start_index=start_index)

@main.route('/prospekte/<int:prospect_id>')
def get_prospect_content(prospect_id):
    prospect = None
    prospect_pages = None
    page_number = None

    filter_args = {
        "prospect_id": prospect_id,
    }
    prospect_pages = Database.search(Prospect_Pages, filter_args=filter_args)

    prospect = Database.search(Prospects, filter_args=filter_args, amount=1)  # get prospect name
    
    page_number = request.args.get('page', default=1, type=int)
    page_number = max(1, min(page_number, len(prospect_pages)))

    return render_template('prospect.html', prospect=prospect, prospect_pages=prospect_pages, page_number=page_number, enumerate=enumerate)

@main.route('/konto')
@login_required
def profile():
    if current_user.is_authenticated:
        return render_template('profile.html', current_user=current_user)
    else:
        return redirect(url_for('main.index'))

@main.route('/einstellungen')
@login_required
def settings():
    if current_user.is_authenticated:
        return render_template('settings.html', current_user=current_user)
    else:
        return redirect(url_for('main.index'))

@main.route('/kontakt')
def contact():
    return render_template('contact.html')

@main.route('/impressum')
def about():
    return render_template('about.html')

@main.route('/robots.txt')
def robots():
    text_content = Tools.load_robots_content()
    return Response(text_content, content_type='text/plain')

@main.route('/sitemap.xml')
def sitemap():
    xml_content = Tools.load_sitemap_content()
    return Response(xml_content, content_type='application/xml')

@main.route('/ads.txt')
@main.route('/Ads.txt')
def ads():
    text_content = "google.com, pub-8697169967636795, DIRECT, f08c47fec0942fa0"
    return Response(text_content, content_type='text/plain')
