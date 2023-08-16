import pymongo
from models import *


### DB INIT ###
def init(db):
    def init_rooms_collection():
        try:
            db.create_collection("rooms")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "rooms", validator=room_validator)
            db.rooms.create_index([("name", pymongo.ASCENDING)], name="room_name", unique=True)
        except Exception as e:
            print(e)
    
    def init_teachers_collection():
        try:
            db.create_collection("teachers")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "teachers", validator=teacher_validator)
            db.teachers.create_index([("name", pymongo.ASCENDING)], name="teacher_unique", unique=True)
        except Exception as e:
            print(e)

    def init_courses_collection():
        try:
            db.create_collection("courses")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "courses", validator=course_validator)
            db.courses.create_index([("code", pymongo.ASCENDING)], name="course_unique", unique=True)
        except Exception as e:
            print(e)

    def init_teach_in_collection():
        try:
            db.create_collection("teach_in")
        except Exception as e:
            print(e)
        
        try:
            db.command("collMod", "teach_in", validator=teach_in_validator)
            db.teach_in.create_index([("teacher_id", pymongo.ASCENDING), ("course_id", pymongo.ASCENDING)], name="teach_in_unique", unique=True)
        except Exception as e:
            print(e)
        
    def init_bookings_collection():
        try:
            db.create_collection("bookings")
        except Exception as e:
            print(e)
        
        try:
            db.command("collMod", "bookings", validator=booking_validator)
            db.bookings.create_index([("schedule_id", pymongo.ASCENDING), ("room_id", pymongo.ASCENDING)], name="booking_unique", unique=True)
        except Exception as e:
            print(e)

    def init_schedules_collection():
        try:
            db.create_collection("schedules")
        except Exception as e:
            print(e)
        
        try:
            db.command("collMod", "schedules", validator=schedule_validator)
            db.schedules.create_index([("course_id", pymongo.ASCENDING), ("start_datetime", pymongo.ASCENDING), ("end_datetime", pymongo.ASCENDING)], name="schedule_unique", unique=True)
        except Exception as e:
            print(e)

    def init_studyplans_collection():
        try:
            db.create_collection("studyplans")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "studyplans", validator=studyplan_validator)
            db.studyplans.create_index([("unit_id", pymongo.ASCENDING), ("semester_id", pymongo.ASCENDING)], name="studyplan_unique", unique=True)
        except Exception as e:
            print(e)

    def init_units_collection():
        try:
            db.create_collection("units")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "units", validator=unit_validator)
            db.units.create_index([("name", pymongo.ASCENDING)], name="unit_unique", unique=True)
        except Exception as e:
            print(e)

    def init_semesters_collection():
        try:
            db.create_collection("semesters")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "semesters", validator=semester_validator)
            db.semesters.create_index([("name", pymongo.ASCENDING)], name="semester_unique", unique=True)
        except Exception as e:
            print(e)

    def init_planned_in_collection():
        try:
            db.create_collection("planned_in")
        except Exception as e:
            print(e)

        try:
            db.command("collMod", "planned_in", validator=planned_in_validator)
            db.planned_in.create_index([("studyplan_id", pymongo.ASCENDING), ("course_id", pymongo.ASCENDING)], name="planned_in_unique", unique=True)
        except Exception as e:
            print(e)
        

    init_rooms_collection()
    init_teachers_collection()
    init_courses_collection()
    init_teach_in_collection()
    init_bookings_collection()
    init_schedules_collection()
    init_studyplans_collection()
    init_units_collection()
    init_semesters_collection()
    init_planned_in_collection()
