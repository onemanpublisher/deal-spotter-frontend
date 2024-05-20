from flask import Blueprint, request
from flask_login import current_user
from urllib.parse import urlparse
from datetime import datetime
import re
import os
# import sys
# sys.path.append("G:\10. Programmierung\6. Python OneManPublisher\Deal_Spotter")
from scripts.utils.omp_tools import OsTools
import logging
from config import CATEGORY_PATH_WIN, CATEGORY_PATH_LIN, ASSETS_PATH, DEBUG
import platform
from . import db, cache
from .models import Prospects, Items
from cachetools import TTLCache
from sqlalchemy.sql import func, or_, asc, desc
from functools import wraps
from collections import defaultdict


system = platform.system()
if system == "Linux":
    CATEGORY_PATH = CATEGORY_PATH_LIN
elif system == "Windows":
    CATEGORY_PATH = CATEGORY_PATH_WIN

#! WORKING CACHE SYSTEM WITH BASIC CACHE | WITHOUT REDIS
# ttlcache = TTLCache(maxsize=100, ttl=21600)  # Adjust maxsize and ttl as needed
# def cached(cache):  # not using cached from cachetools because it wont work with arguments like dict
#     def decorator(func):
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             # Convert the filter_args dictionary to a frozenset
#             filter_args = kwargs.get('filter_args')
#             if filter_args:
#                 kwargs['filter_args'] = frozenset(filter_args.items())

#             where_conditions = kwargs.get('where_conditions')
#             if where_conditions:
#                 kwargs['where_conditions'] = frozenset(where_conditions.items())
#             key = (frozenset(args), frozenset(kwargs.items()))
#             # print("###key which is cached")
#             # print(key)
#             if key in cache:
#                 return cache[key]
#             result = func(*args, **kwargs)
#             cache[key] = result
#             return result
#         return wrapper
#     return decorator
#! /WORKING CACHE SYSTEM WITH BASIC CACHE | WITHOUT REDIS

#! WORKING CACHE SYSTEM WITH REDIS
def cached(timeout=21600):
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate a cache key based on function name and arguments
            cache_key = f"{args}:{kwargs}"
            # Try to get the result from the cache
            result = cache.get(cache_key)
            # If the result is not in the cache, compute it and store in the cache
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout=timeout)
                # print("###key which is cached")
                # print(cache_key)
            
            return result
        return wrapper
    return decorator
#! /WORKING CACHE SYSTEM WITH REDIS

tools = Blueprint('tools', __name__)

@tools.app_context_processor
@cache.cached(timeout=86400, key_prefix='load_categories_keys')  # Cache for 1 day
def load_categories_keys():
    data = OsTools.load_json_file(CATEGORY_PATH)
    list_categories = set()
    for key in data.keys():
        if key:
            list_categories.add(key)
    return {"load_categories_keys": list(sorted(list_categories))}

@tools.app_context_processor
@cache.cached(timeout=86400, key_prefix='load_available_markets')  # Cache for 1 day
def load_available_markets():
    filter_args = Tools.load_locations_filter_args()
    all_prospects = Database.search(Prospects, filter_args=filter_args)

    prospect_set = set()  # Using a set to ensure uniqueness
    for prospect in all_prospects:
        prospect_set.add(prospect.name)
    return {"load_available_markets": list(sorted(prospect_set))}

@tools.app_context_processor
def load_available_markets_counts():
    filter_args = Tools.load_locations_filter_args()
    all_prospects = Database.search(Prospects, filter_args=filter_args)
    market_counts = defaultdict(int)
    for prospect in all_prospects:
        market_name = prospect.name
        generated_items_count = prospect.generated_items or 0
        market_counts[market_name] += generated_items_count
    return {"load_available_markets_counts": market_counts}

@tools.app_context_processor
def load_available_categories_counts():
    filter_args = Tools.load_locations_filter_args()
    all_items = Database.search(Items, filter_args=filter_args)

    category_counts = defaultdict(int)

    for item in all_items:
        categories = item.category.split(',') if item.category else []
        if not categories:
            category_counts["Ohne Kategorie"] += 1
            continue
        for category in categories:
            category_counts[category.strip()] += 1

    category_counts_dict = dict(category_counts)

    return {"load_available_categories_counts": category_counts_dict}

@tools.app_context_processor
@cache.cached(timeout=86400, key_prefix='get_current_year')  # Cache for 1 day
def get_current_year():
    return {"get_current_year": datetime.now().year}

@tools.app_context_processor
@cache.cached(timeout=3600, key_prefix='get_current_date')  # Cache for 1 hour
def get_current_date():
    return {"get_current_date": datetime.now().strftime("%d-%m-%Y")}

@tools.app_context_processor
@cache.cached(timeout=36000, key_prefix='get_base_url')  # Cache for 10 hour
def get_base_url():
    base_url = request.base_url
    parsed_url = urlparse(base_url)
    hostname = parsed_url.hostname
    return {"get_base_url": hostname}

@tools.app_context_processor
def get_current_url():
    url_path = urlparse(request.url).path
    if url_path == '/':
        return dict(get_current_url='/')
    else:
        subpage = url_path.strip('/').split('/')[0]
        return dict(get_current_url=subpage)

@tools.app_context_processor
def get_current_full_url():
    url_path = urlparse(request.url).path
    if url_path == '/':
        return dict(get_current_full_url='/')
    else:
        return dict(get_current_full_url=url_path)

class Tools:
    @staticmethod
    def email_check(email):
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        # pass the regular expression
        # and the string into the fullmatch() method
        if(re.fullmatch(regex, email)):
            return True
        else:
            return False

    @staticmethod
    def password_check(password):
        """
        Verify the strength of 'password'
        Returns a dict indicating the wrong criteria
        A password is considered strong if:
            8 characters length or more
            1 digit or more
            1 symbol or more
            1 uppercase letter or more
            1 lowercase letter or more
        Args:
            password ([str]): [description]

        Returns:
            [str]: [description]
        """
        length_error = len(password) < 8  # calculating the length
        digit_error = re.search(r"\d", password) is None  # searching for digits
        # uppercase_error = re.search(r"[A-Z]", password) is None  # searching for uppercase
        lowercase_error = re.search(r"[a-z]", password) is None  # searching for lowercase
        #symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~" + r'"]', password) is None  # searching for symbols

        password_ok = not (length_error or digit_error or lowercase_error)
        return password_ok

    @staticmethod
    def paginate(items, page_number, page_size):
        if items:
            start_index = (page_number - 1) * page_size
            end_index = start_index + page_size
            return items[start_index:end_index]
        else:
            return None

    @staticmethod
    def filter_profanity(text):
        return OsTools.filter_profanity(text)
    
    @staticmethod
    def append_and_save_to_file(file_path, key, value, encoding="utf16"):
        return OsTools.append_and_save_to_file(file_path=file_path, key=key, value=value, encoding=encoding)

    @staticmethod
    @cache.cached(timeout=86400, key_prefix='load_xml_content')  # Cache for 1 day
    def load_sitemap_content():
        with open(os.path.abspath(os.path.join(ASSETS_PATH, "sitemap.xml")), 'r') as xml_file:
            xml_data = xml_file.read()
        return xml_data    
    
    @staticmethod
    @cache.cached(timeout=86400, key_prefix='load_robots_content')  # Cache for 1 day
    def load_robots_content():
        with open(os.path.abspath(os.path.join(ASSETS_PATH, "robots.txt")), 'r') as xml_file:
            xml_data = xml_file.read()
        return xml_data

    @staticmethod
    @cached()
    def fetch_categorised_items(selected_market, selected_category, selected_sub_category, filter_args):  # included filter_args because of cache otherwise it wont detect changes on location
        if not filter_args: filter_args={}  # set if selected_market is none the filters also to none for cache. if {} is parsed it wont work

        if selected_category == "Ohne Kategorie":
            filter_args["category"] = ""
            keyword = ""  #! resets the name for the query
        # elif selected_category == "Alle Kategorien":
        #     filter_args = defaultdict(str)
        #     keyword = ""
        else:
            keyword = selected_category  # using this method because some categories containing multiple categories and can't search directly for so use keyword

        # if type(selected_sub_category) == str and selected_sub_category != "Alle Unterkategorien":
        if type(selected_sub_category) == str:
            filter_args["sub_category"] = selected_sub_category

        # if type(selected_market) == str and selected_market != "Alle Märkte":
        if type(selected_market) == str:
            filter_args["market"] = selected_market

        available = Tools.check_if_locations_prospects_available(filter_args.get("location_id", 0))
        if not available:
            filter_args["location_id"] = 0
        items = Database.search(Items, filter_args=filter_args, keyword=keyword)
        return items

    @staticmethod
    def load_sub_categories_keys(category, market):
        """use category and market for it

        Args:
            category (_type_): _description_
            market (_type_): _description_

        Returns:
            _type_: _description_
        """
        filter_args = defaultdict(str)
        if category: filter_args["category"] = category
        if market: filter_args["market"] = market

        filter_args = Tools.load_locations_filter_args(filter_args)
        all_items = Database.search(Items, filter_args=filter_args)

        list_sub_categories = set()
        for item in all_items:
            if item.sub_category != None or item.sub_category != "None":
                list_sub_categories.add(item.sub_category)
        return list(sorted(list_sub_categories))

    @staticmethod
    def load_locations_filter_args(filter_args=None, set=None):
        """use "set" to set location_id to 0

        Args:
            filter_args (_type_, optional): _description_. Defaults to None.
            set (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        if not filter_args:
            filter_args = {}

        if set != None:
            filter_args["location_id"] = 0
        elif current_user.is_authenticated and current_user.location_id:
            filter_args["location_id"] = current_user.location_id
        elif request.cookies.get("location_id"):
            filter_args["location_id"] = request.cookies.get("location_id")
        else:
            filter_args["location_id"] = 0
            
        available = Tools.check_if_locations_prospects_available(filter_args["location_id"])
        if available:
            return filter_args
        else:
            filter_args["location_id"] = 0
            return filter_args

    @staticmethod
    @cached()
    def check_if_locations_prospects_available(location_id):
        filter_args = {"location_id": location_id}
        available = Database.search(Prospects, filter_args=filter_args, amount=1)
        if available:
            return True
        return False

class Database:
    @staticmethod
    @cached()
    # @cached(ttlcache)
    def search(model, filter_args: dict = None, keyword=None, search_columns=None, amount=None, random_order=False, sort_by_datetime=False, where_conditions: dict=None):
        """
        Search for elements in the database based on various criteria using caching.

        :param model: SQLAlchemy model for the target table
        :param filter_args: Dictionary containing filter conditions as keyword arguments
        :param keyword: Keyword to search for using LIKE (optional)
        :param column: Column name to search in (optional, required if using keyword search)
        :param amount: Maximum number of results to return (optional)
        :param random_order: Whether to order the results randomly (optional)
        :param where_conditions: USE KEY "where" FOR WHERE CONDITION AND ALL OTHER VALUES ARE GOING TO BE INSERTED INTO A OR COMBINATION
        :return: List of query results
        """
        with db.session() as session:  # Use a session context manager
            query = Database.__build_query(session, model, filter_args, keyword, search_columns, amount, random_order, sort_by_datetime, where_conditions)
        return query

    @staticmethod
    def search_without_cache(model, filter_args: dict = None, keyword=None, search_columns=None, amount=None, random_order=False, sort_by_datetime=False, where_conditions: dict=None):
        """
        Search for elements in the database based on various criteria without caching.

        :param model: SQLAlchemy model for the target table
        :param filter_args: Dictionary containing filter conditions as keyword arguments
        :param keyword: Keyword to search for using LIKE (optional)
        :param column: Column name to search in (optional, required if using keyword search)
        :param amount: Maximum number of results to return (optional)
        :param random_order: Whether to order the results randomly (optional)
        :return: List of query results
        """
        with db.session() as session:  # Use a session context manager
            query = Database.__build_query(session, model, filter_args, keyword, search_columns, amount, random_order, sort_by_datetime, where_conditions)
        return query

    @staticmethod
    def __build_query(session, model, filter_args: dict = None, keyword=None, search_columns=None, amount=None, random_order=False, sort_by_datetime=False, where_conditions: dict=None):
        if DEBUG:
            print(f"using query to access db data from {model} with following args: filter_args: {filter_args}, keyword: {keyword}, search_columns: {search_columns}, amount: {amount}, random_order: {random_order}, where_conditions: {where_conditions}")
            logging.debug(f"using query to access db data from {model} with following args: filter_args: {filter_args}, keyword: {keyword}, search_columns: {search_columns}, amount: {amount}, random_order: {random_order}, where_conditions: {where_conditions}")

        query = session.query(model)

        # Apply filter conditions if provided
        if filter_args:
            filter_args = dict(filter_args)  # Convert frozenset back to dict
            query = query.filter_by(**filter_args)

        # Apply keyword search using LIKE if keyword and column are provided
        if keyword:
            if search_columns is None:
                category_to_column = {
                    "name": model.name,
                    "category": model.category,
                    "sub_category": model.sub_category,
                    "market": model.market
                }
                search_columns = category_to_column.values()

            # Construct the filter conditions for the specified columns
            or_conditions = [column.ilike(f"%{keyword}%") for column in search_columns]

            # Apply the OR conditions to the query
            query = query.filter(or_(*or_conditions))

        if where_conditions:
            where_conditions = dict(where_conditions)
            if not where_conditions["where"]:
                print("got no where statement set in the dict")
                logging.warning("got no where statement set in the dict")
            else:
                where_statement = where_conditions["where"]
                del where_conditions["where"]
                and_conditions = [getattr(model, where_statement) == value for value in where_conditions.values()]
                query = query.filter(or_(*and_conditions))

        # Apply random order if requested
        if random_order:
            query = query.order_by(func.random())

        if sort_by_datetime:  #! SORTING CURRENTLY BY UPVOTES AND DATETIME
            # Sort the results by "upvotes" (descending) and then by "datetime" (ascending)
            query = query.order_by(desc(model.upvotes), asc(model.datetime))

        # Limit the number of results if amount is specified
        if amount is not None:
            query = query.limit(amount)
        if amount == 1:
            return query.first()

        return query.all()

    #! WORKING CACHE SYSTEM WITH BASIC CACHE | WITHOUT REDIS
    # @staticmethod
    # def delete_cache(model, *args, **kwargs):
    #     """Deletes the cached result of a function decorated with `cached`."""
    #     # Convert the filter_args dictionary to a frozenset of tuples
    #     filter_args = kwargs.get('filter_args')
    #     if filter_args:
    #         kwargs['filter_args'] = frozenset(tuple(filter_args.items()))

    #     where_conditions = kwargs.get('where_conditions')
    #     if where_conditions:
    #         kwargs['where_conditions'] = frozenset(where_conditions.items())
    #     key = (frozenset((model,)), frozenset(kwargs.items()))
    #     # print("!!!key which is going to be deleted in cache")
    #     # print(key)
    #     if key in ttlcache:
    #         del ttlcache[key]
    #         print(f"deleted cache with key {key}")
    #         logging.info(f"deleted cache with key {key}")
    #! /WORKING CACHE SYSTEM WITH BASIC CACHE | WITHOUT REDIS

    #! WORKING CACHE SYSTEM WITH REDIS
    @staticmethod
    def delete_cache(*args, **kwargs):
        cache_key = f"{args}:{kwargs}"
        # print("!!!key which is going to be deleted in cache")
        print(f"deleted cache with key {cache_key}")
        logging.info(f"deleted cache with key {cache_key}")
        cache.delete(cache_key)

    @staticmethod
    def clear_cache():
        cache.clear()
    #! /WORKING CACHE SYSTEM WITH REDIS
