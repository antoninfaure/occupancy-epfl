import pymongo
from pymongo import MongoClient
import config
import requests
from bs4 import BeautifulSoup
import numpy as np
import re
import pickle 
from urllib.parse import urlparse, parse_qs

client = MongoClient(f"mongodb+srv://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_URL}/?retryWrites=true&w=majority")

db = client[config.DB_NAME]

DB_indices(db)

rooms_filter = [
    'POL.N3.E',
    'POL315.1',
    'PHxx',
    'Max412',
    'STCC - Garden Full',
    'ELG124',
    'EXTRANEF126',
    'CHCIGC'
]

rooms_map = {
    'CE1': 'CE11',
    'CM4': 'CM14',
    'BC07-08': ['BC07','BC08'],
    'CM3': 'CM13',
    'CE4': 'CE14',
    'CM2': 'CM12',
    'SG1': 'SG1138',
    'CE6': 'CE16',
    'CM5': 'CM15',
    'CE5': 'CE15',
    'CM1': 'CM11',
    'CE2': 'CE12',
    'CE3': 'CE13',
    'RLC E1 240': 'RLCE1240'
}

map_semester = {
    'Bachelor 1': 'BA1',
    'Bachelor 2' : 'BA2',
    'Bachelor 3' : 'BA3',
    'Bachelor 4' : 'BA4',
    'Bachelor 5' : 'BA5',
    'Bachelor 6' : 'BA6',
}

map_section = {
    'Génie mécanique': 'GM',
    'Architecture': 'AR',
    'Chimie et génie chimique': 'CGC',
    'Génie civil': 'GC',
    'Génie électrique et électronique ': 'EL',
    'Informatique': 'IN',
    'Ingénierie des sciences du vivant': 'SV',
    'Mathématiques': 'MA',
    'Microtechnique': 'MT',
    'Physique': 'PH',
    'Science et génie des matériaux': 'MX',
    "Sciences et ingénierie de l'environnement": 'SIE',
    'Systèmes de communication': 'SC',
    'Chimie': 'CGC',
    'Génie chimique': 'CGC'
 }

# -- Get data for all courses on edu.epfl.ch with schedule information -- #

# List all courses url
courses_url = getAllCours()

# Filter unique
courses_url = list(set(courses_url))

# Parse all courses
URL_ROOT = 'https://edu.epfl.ch/coursebook/fr/'
courses = []
for url in courses_url:
    courses.append(parseCours(URL_ROOT + url))

# Filter None 
data = list(filter(lambda x: x != None, courses))


# -- List all entities and relations -- #

# List entities
rooms, teachers, courses = list_entities(data)

# Save our entities to DB
update_db_entities(db, rooms, teachers, courses)

# List relations
teach_in, booking = list_relations(data)

# Save our relations to DB
update_relations_db(db, teach_in, booking)


# -- Assign room type based on plan.epfl.ch -- #

# Find all XML room objects
rooms_xml = parse_all_levels()

# Parse all XML room objects and list all unique types
rooms_parsed = parse_all_rooms(rooms_xml)

# Update all rooms in our DB with their type
update_rooms_type(db, rooms_parsed)


# -- List all study plans on edu.epfl.ch -- #

# List all study plans
study_plans = list_plans()

# Update study plans in DB
update_plans_db(db, study_plans)