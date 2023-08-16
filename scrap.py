from utils import *
from pymongo import MongoClient
from config import *
import config
from tqdm import tqdm
from datetime import datetime
import db_utils

client = MongoClient(f"mongodb+srv://{DB_USER}:{DB_PASSWORD}@{DB_URL}/?retryWrites=true&w=majority")

db = client[DB_NAME]

db_utils.init(db)

### -- Create the semesters -- ###

# Fall 2023-2024
create_new_semester(db,
    name="Semestre d'automne 2023-2024",
    start_date=datetime(2023, 9, 19),
    end_date=datetime(2023, 12, 22),
    type="fall",
    available=True
)

# Spring 2023-2024
create_new_semester(db,
    name="Semestre de printemps 2023-2024",
    start_date=datetime(2024, 2, 19),
    end_date=datetime(2024, 5, 31),
    type="spring",
    available=True
)

### -- Get data for all courses on edu.epfl.ch with schedule information -- ###

# List all courses url
courses_url = getAllCoursesUrl()

# Filter unique
courses_url = list(set(courses_url))

# Parse all courses
URL_ROOT = 'https://edu.epfl.ch'
courses = []
for url in tqdm(courses_url, total=len(courses_url)):
    courses.append(parseCourse(URL_ROOT + url))

# Filter duplicates
courses = filter_duplicates_courses(courses)

### -- Create all courses -- ###
create_courses(db, courses)

### -- Create all rooms -- ###
create_rooms(db, courses)

### -- Create all teachers -- ###
create_teachers(db, courses)

### -- Create all bookings and schedules -- ###
create_courses_schedules_and_bookings(db, courses)

### -- Create all teach_in -- ###
create_teach_in(db, courses)

### -- List planned_in -- ###
planned_in = list_courses_plan_studyplans()

### -- Create all units -- ###
create_units(db, planned_in)

### -- Create all studyplans -- ###
create_studyplans(db, planned_in)

### -- Create all planned_in -- ###
create_planned_in(db, planned_in)