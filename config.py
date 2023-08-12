from os import environ
from dotenv import load_dotenv
load_dotenv()

DB_USER = environ.get('DB_USER')
DB_PASSWORD = environ.get('DB_PASSWORD')
DB_URL = environ.get('DB_URL')
DB_NAME = environ.get('DB_NAME')
SECRET_KEY = environ.get('SECRET_KEY')

ROOMS_FILTER = [
    'POL.N3.E',
    'POL315.1',
    'PHxx',
    'Max412',
    'STCC - Garden Full',
    'ELG124',
    'EXTRANEF126',
    'CHCIGC'
]

MAP_ROOMS = {
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

MAP_PROMOS = {
    'Bachelor 1': 'BA1',
    'Bachelor 2' : 'BA2',
    'Bachelor 3' : 'BA3',
    'Bachelor 4' : 'BA4',
    'Bachelor 5' : 'BA5',
    'Bachelor 6' : 'BA6',
    'Master 1' : 'MA1',
    'Master 2' : 'MA2',
    'Master 3' : 'MA3',
    'Master 4' : 'MA4',
    'PDM Printemps' : 'PMH',
    'PDM Automne' : 'PME',
}

MAP_SECTIONS = {
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
    'Génie chimique': 'CGC',
    'Chimie moléculaire et biologique': 'CGC',
    'Humanités digitales': 'HD',
    'Data Science': 'DS',

 }

MAP_SEMESTERS = {
    'BA1': 'fall',
    'BA2': 'spring',
    'BA3': 'fall',
    'BA4': 'spring',
    'BA5': 'fall',
    'BA6': 'spring',
    'MA1': 'fall',
    'MA2': 'spring',
    'MA3': 'fall',
    'MA4': 'spring',
    'PMH': 'fall',
    'PME': 'spring',
}
