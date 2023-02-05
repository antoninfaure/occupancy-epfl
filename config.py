from os import environ
from dotenv import load_dotenv
load_dotenv()

DB_USER = environ.get('DB_USER')
DB_PASSWORD = environ.get('DB_PASSWORD')
DB_URL = environ.get('DB_URL')
DB_NAME = environ.get('DB_NAME')
SECRET_KEY = environ.get('SECRET_KEY')