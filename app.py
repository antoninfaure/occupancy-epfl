from flask import request, Flask, render_template, redirect, url_for, abort, jsonify
from flask_pymongo  import PyMongo, MongoClient
import pickle 
from datetime import datetime, timedelta, time as dt_time
import numpy as np
import re
from copy import deepcopy
from bson.objectid import ObjectId
import time as t_time
from flask_cors import CORS

app = Flask(__name__)
app.config.from_pyfile('config.py')
client = MongoClient(f"mongodb+srv://{app.config.get('DB_USER')}:{app.config.get('DB_PASSWORD')}@{app.config.get('DB_URL')}/?retryWrites=true&w=majority")
CORS(app, resources={r"/api/*": {"origins": ["https://antoninfaure.github.io", "http://localhost:3000", "https://occupancy.flep.ch"]}})

db = client[app.config.get('DB_NAME')]

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/api/rooms', methods=['GET'])
def rooms():

    # List all rooms
    rooms = list(db.rooms.find({ "available": True }))

    # replace ObjectId _id with string _id
    for room in rooms:
        room['_id'] = str(room['_id'])

    return jsonify(rooms)


@app.route('/api/courses', methods=['GET'])
def courses():
    # List all courses with their semester
    courses = list(db.planned_in.aggregate([
        {
            "$match": {
                "available": True
            }
        },
        {
            "$group": {
                "_id": "$course_id",
                "studyplan_id": { "$first": "$studyplan_id" } # only consider the first studyplan_id
            }
        },
        {
            "$lookup": {
                "from": "courses",
                "localField": "_id",
                "foreignField": "_id",
                "as": "courseDetails"
            }
        },
        {
            "$lookup": {
                "from": "studyplans",
                "localField": "studyplan_id",
                "foreignField": "_id",
                "as": "studyplanDetails"
            }
        },
        {
            "$lookup": {
                "from": "semesters",
                "localField": "studyplanDetails.semester_id",
                "foreignField": "_id",
                "as": "semesterDetails"
            }
        },
        {
            "$unwind": "$courseDetails"
        },
        {
            "$unwind": "$semesterDetails" 
        },
        {
            "$project": { # set courseDetails as root and semesterDetails as semester
                "_id": 0, 
                "mergedDoc": { "$mergeObjects": ["$$ROOT", "$courseDetails"] },
                "semester": "$semesterDetails"
            }
        },
        {
            "$replaceRoot": { # replace root with mergedDoc
                "newRoot": {
                    "$mergeObjects": ["$mergedDoc", { "semester": "$semester" }]
                }
            }
        },
        {
            "$project": { # remove unnecessary fields
                "mergedDoc": 0,
                "semesterDetails": 0,
                "studyplanDetails": 0,
                "courseDetails": 0,
                "studyplan_id": 0,
            }
        }
    ]))
    
    courses_with_studyplan_ids = [course['_id'] for course in courses]

    course_without_studyplan_with_schedules = list(db.course_schedules.aggregate([
        {
            "$match": {
                "available": True,
                "course_id": { "$nin": courses_with_studyplan_ids }
            }
        },
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "courseDetails"
            }
        },
        {
            "$unwind": "$courseDetails"
        },
        {
            "$group": {
                "_id": "$course_id",
                "name": { "$first": "$courseDetails.name" },
                "code": { "$first": "$courseDetails.code" },
                "credits": { "$first": "$courseDetails.credits" },
                "edu_url": { "$first": "$courseDetails.edu_url" }
            }
        },
        {
            "$project": {
                "_id": 0,
                "_id": "$_id",
                "name": 1,
                "code": 1,
                "credits": 1,
                "edu_url": 1
            }
        }
    ]))

    courses.extend(course_without_studyplan_with_schedules)

    courses = list(courses)

    # replace ObjectId _id with string _id
    for course in courses:
        course['_id'] = str(course['_id'])
        if 'semester' in course:
            course['semesterType'] = course['semester']['type']
            course['semester'] = course['semester']['name']

    return jsonify(courses)

@app.route('/api/studyplans', methods=['GET'])
def studyplans():
    # List all studyplans with their semester
    studyplans = list(db.studyplans.aggregate([
        {
            "$lookup": {
                "from": "etu_units",
                "localField": "unit_id",
                "foreignField": "_id",
                "as": "unit"
            }
        },
        {
            "$lookup": {
                "from": "semesters",
                "localField": "semester_id",
                "foreignField": "_id",
                "as": "semester"
            }
        },
        {
            "$match": {
                "available": True
            }
        }
    ]))

    # replace ObjectId _id with string _id
    for studyplan in studyplans:
        studyplan['_id'] = str(studyplan['_id'])
        studyplan.pop('unit_id')
        studyplan.pop('semester_id')
        studyplan['promo'] = studyplan['unit'][0]['promo']
        studyplan['section'] = studyplan['unit'][0]['section']
        studyplan['name'] = studyplan['unit'][0]['name']
        studyplan.pop('unit')
        studyplan['semesterType'] = studyplan['semester'][0]['type']
        studyplan['semester'] = studyplan['semester'][0]['name']

    return jsonify(studyplans)

@app.route('/api/rooms/<name>', methods=['GET'])
def room(name):
    if (name == None):
        return abort(400)

    name = re.sub(r"(?![A-Za-z0-9\-\.])", "", name)
 
    room = db.rooms.find_one({'name': name, "available": True })

    if (room == None):
        return abort(404)

    try:
        room_course_bookings = list(db.course_bookings.find({
            'room_id': room['_id'],
        }))

        course_schedules = list(db.course_schedules.aggregate([
            {
                "$match": {
                    '_id': { '$in': [ObjectId(booking['schedule_id']) for booking in room_course_bookings] }
                }
            },
            {
                "$lookup": {
                    "from": "courses",
                    "localField": "course_id",
                    "foreignField": "_id",
                    "as": "course"
                }
            }
        ]))

        room_event_bookings = list(db.event_bookings.find({
            'room_id': room['_id'],
        }))
        event_schedules = list(db.event_schedules.aggregate([
            {
                "$match": {
                    '_id': { '$in': [ObjectId(booking['schedule_id']) for booking in room_event_bookings] },
                    'visible': True,
                    'available': True,
                    'status': 0
                }
            },
            {
                "$lookup": {
                    "from": "roles",
                    "localField": "role_id",
                    "foreignField": "_id",
                    "as": "role"
                }
            },
            {
                # Get the role unit
                "$lookup": {
                    "from": "units",
                    "localField": "role.unit_id",
                    "foreignField": "_id",
                    "as": "unit"
                }
            }   
        ]))


    except Exception as e:
        print(e)

    # Get the soonest booking start date
    schedules = course_schedules + event_schedules
    if len(schedules) > 0:
        start_date = min([schedule['start_datetime'] for schedule in schedules]).date()
        end_date = max([schedule['end_datetime'] for schedule in schedules]).date()
    else:
        start_date = datetime.now().date()
        end_date = datetime.now().date()
    
    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule.pop('course_id')
        schedule['course'] = schedule['course'][0]
        schedule['course'].pop('_id')
        schedule['start'] = (schedule['start_datetime'] + timedelta(minutes=15)).isoformat()
        schedule['end'] = schedule['end_datetime'].isoformat()

    room['_id'] = str(room['_id'])
    room['schedules'] = schedules

    return jsonify(room) 

@app.route('/api/rooms/find_free_rooms', methods=['POST'])
def find_free_rooms():
    selection = request.json
    if (selection == None):
        return abort(400)

    print(selection)

    if (type(selection) != list):
        return abort(400)

    if (len(selection) > 0 and type(selection[0]) != dict):
        return abort(400)
    
    # Convert selection to datetime ranges
    datetime_ranges = []
    for item in selection:
        start_time = item["start"].replace('Z', '+00:00')
        end_time = item["end"].replace('Z', '+00:00')
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.fromisoformat(end_time)
        datetime_ranges.append({"start": start_datetime, "end": end_datetime})
       
    # Find all rooms that are booked during the datetime ranges
    query_conditions = []
    for date_range in datetime_ranges:
        query_conditions.append({
            "$and": [
                {"start_datetime": {"gte": date_range["end"]}},
                {"end_datetime": {"$lte": date_range["start"]}}
            ]
        })

    if (len(query_conditions) == 0):
        free_rooms = list(db.rooms.find({ "available": True }))
        rooms_names = [{'name': x['name'], 'type': x['type']} for x in free_rooms]
        return rooms_names
    
    ## COURSES
    # course schedules during constraining ranges
    constraining_course_schedules = list(db.course_schedules.find({"$or": query_conditions, 'available': True}))
    constraining_course_schedules_ids = [schedule["_id"] for schedule in constraining_course_schedules]

    # rooms booked for these course schedules
    course_booked_rooms = db.course_bookings.find({"schedule_id": {"$in": constraining_course_schedules_ids}})
    course_booked_room_ids = [booking["room_id"] for booking in course_booked_rooms]

    ## EVENTS
    # event schedules during constraining ranges
    constraining_event_schedules = list(db.event_schedules.find({"$or": query_conditions, 'status': 0, 'visible': True, 'available': True}))
    constraining_event_schedules_ids = [schedule["_id"] for schedule in constraining_event_schedules]

    # rooms booked for these event schedules
    event_booked_rooms = db.event_bookings.find({"schedule_id": {"$in": constraining_event_schedules_ids}})
    event_booked_room_ids = [booking["room_id"] for booking in event_booked_rooms]


    # Find available rooms
    booked_rooms_ids = course_booked_room_ids + event_booked_room_ids
    free_rooms = list(db.rooms.find({"available": True, "_id": {"$nin": booked_rooms_ids}}))
    rooms_names = [{'name': x['name'], 'type': x['type']} for x in list(free_rooms)]

    return rooms_names


@app.route('/api/courses/<code>', methods=['GET'])
def find_course(code):
    if (code == None):
        return abort(400)

    course = db.courses.find_one({ 'code' : code, 'available': True})

    if (course == None):
        return abort(404)
    
    # find the plannedin that contains this course and populate the studyplan, then find the semester of the studyplan
    semester = list(db.planned_in.aggregate([
        {
            "$match": {
                'course_id': course['_id'],
                'available': True
            }
        },
        {
            "$lookup": {
                "from": "studyplans",
                "localField": "studyplan_id",
                "foreignField": "_id",
                "as": "studyplan"
            }
        },
        {
            "$unwind": "$studyplan"
        },
        {
            "$lookup": {
                "from": "semesters",
                "localField": "studyplan.semester_id",
                "foreignField": "_id",
                "as": "semester"
            }
        },
        {
            "$unwind": "$semester"
        },
        {
        "$project": {
                "_id": 0,
                "semester": 1
            }
        },
        {
            "$limit": 1
        }
    ]))
    
    if semester != None and len(semester) > 0:
        semester = semester[0]['semester']
        course['semester'] = semester
    else:
        semester = None

    # list teachers
    teachers = list(db.teach_in.aggregate([
        {
            "$match": {
                'course_id': course['_id'],
                'available': True
            }
        },
        {
            "$lookup": {
                "from": "teachers",
                "localField": "teacher_id",
                "foreignField": "_id",
                "as": "teacher"
            }
        },
        {
            "$unwind": "$teacher"
        },
        {
            "$project": {
                "_id": 0,
                "teacher": 1
            }
        }
    ]))

    course['teachers'] = [teacher['teacher'] for teacher in teachers if teacher != None]

    schedules = list(db.course_schedules.aggregate([
            {
                "$match": {
                    'course_id': course['_id'],
                    'available': True
                }
            },
            {
                "$lookup": {
                    "from": "course_bookings",
                    "localField": "_id",
                    "foreignField": "schedule_id",
                    "as": "bookings"
                }
            },
            {
                "$unwind": "$bookings"
            },
            {
                "$lookup": {
                    "from": "rooms",
                    "localField": "bookings.room_id",
                    "foreignField": "_id",
                    "as": "room"
                }
            },
            {
                "$unwind": "$room"
            }, 
            {
            "$group": {
                "_id": "$_id",
                "rooms": {"$push": "$room.name"},
                "originalDoc": {"$first": "$$ROOT"}
            }
        },
        {
            "$replaceRoot": {
                "newRoot": {
                    "$mergeObjects": ["$originalDoc", {"rooms": "$rooms"}] 
                }
            }
        },
        {
            "$project": {
                "bookings": 0,
                "room": 0
            }
        }
    ]))

    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule.pop('course_id')
        schedule['start'] = (schedule['start_datetime'] + timedelta(minutes=15)).isoformat()
        schedule['end'] = schedule['end_datetime'].isoformat()

    course['_id'] = str(course['_id'])
    if semester != None:
        course['semester'].pop('_id')
    
    for teacher in course['teachers']:
        teacher.pop('_id')
    course['schedules'] = schedules
  

    return jsonify(course)

@app.route('/api/studyplans/<studyplan_id>', methods=['GET'])
def find_studyplan(studyplan_id):
    if (studyplan_id == None):
        return abort(400)
    
    studyplan = list(db.studyplans.aggregate([
        {
            "$match": {
                '_id': ObjectId(studyplan_id)
            }
        },
            {
            "$lookup": {
                "from": "etu_units",
                "localField": "unit_id",
                "foreignField": "_id",
                "as": "unit"
            }
        },
        {
            "$lookup": {
                "from": "semesters",
                "localField": "semester_id",
                "foreignField": "_id",
                "as": "semester"
            }
        },
        {
            "$unwind": "$unit"
        },
        {
            "$unwind": "$semester"
        }
    ]))

    if (len(studyplan) == 0):
        return abort(404)
    
    studyplan = studyplan[0]

    if (studyplan == None):
        return abort(404)


    # Find all courses in studyplan
    pipeline = [
        {
            "$match": {
                'studyplan_id': studyplan['_id']
            }
        },
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course_info"
            }
        },
        {
            "$unwind": "$course_info"
        },
        {
            "$replaceRoot": { "newRoot": "$course_info" }
        }
    ]

    courses_in_studyplan = list(db.planned_in.aggregate(pipeline))

    if (len(courses_in_studyplan) == 0):
        return abort(404)
    
    # Find semester
    semester = db.semesters.find_one({ '_id': studyplan['semester_id'] })

    if (semester == None):
        print("semester not found")
        return abort(404)

    # Get the schedules with populated rooms and course info
    schedules = list(db.course_schedules.aggregate([
        {
            "$match": {
                'course_id': {'$in': list(map(lambda x: x['_id'], courses_in_studyplan))},
                'available': True
            }
        },
        {
            "$lookup": {
                "from": "courses",
                "localField": "course_id",
                "foreignField": "_id",
                "as": "course"
            }
        },
        {
            "$unwind": "$course"
        },
        {
            "$lookup": {
                "from": "course_bookings",
                "localField": "_id",
                "foreignField": "schedule_id",
                "as": "bookings"
            }
        },
        {
            "$unwind": {
                "path": "$bookings",
                "preserveNullAndEmptyArrays": True  # keeps schedules that might not have bookings
            }
        },
        {
            "$lookup": {
                "from": "rooms",
                "localField": "bookings.room_id",
                "foreignField": "_id",
                "as": "room"
            }
        },
        {
            "$unwind": {
                "path": "$room",
                "preserveNullAndEmptyArrays": True  # keeps schedules/bookings that might not have rooms
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "rooms": {"$push": "$room.name"}, 
                "originalDoc": {"$first": "$$ROOT"} 
            }
        },
        {
            "$replaceRoot": {
                "newRoot": {
                    "$mergeObjects": ["$originalDoc", {"rooms": "$rooms"}]
                }
            }
        },
        {
            "$project": {
                "bookings": 0,
                "room": 0 
            }
        }
    ]))

    for schedule in schedules:
        schedule['_id'] = str(schedule['_id'])
        schedule.pop('course_id')
        schedule['start'] = (schedule['start_datetime'] + timedelta(minutes=15)).isoformat()
        schedule['end'] = schedule['end_datetime'].isoformat()
        schedule['course'].pop('_id')
    
    studyplan['schedules'] = schedules


    studyplan['_id'] = str(studyplan['_id'])
    studyplan.pop('unit_id')
    studyplan.pop('semester_id')

    studyplan['unit'].pop('_id')
    
    studyplan['semesterType'] = semester['type']
    studyplan['semester'] = semester['name']

    return jsonify(studyplan)

    

@app.errorhandler(404)
def page_not_found(e):
    return jsonify(error=str(e)), 404

if __name__ == "__main__":
    app.run(debug=True)