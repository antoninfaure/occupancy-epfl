from utils import DB_init
from pymongo import MongoClient
from config import *

client = MongoClient(f"mongodb+srv://{DB.get('USER')}:{DB.get('PASSWORD')}@{DB.get('URL')}/?retryWrites=true&w=majority")

db = client[DB.get('NAME')]

DB_init(db)

