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
CORS(app, resources={r"/api/*": {"origins": ["https://antoninfaure.github.io", "https://occupancy.flep.ch", "https://lm.polysource.ch"]}})
#CORS(app, resources={r"/api/*": {"origins": "*"}})

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
    # List all planned_in with their studyplan
    courses = list(db.planned_in.aggregate([
        {
        "$match": {
            "available": True
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
        "$group": {
            "_id": "$course_id",
            "courseDocument": { "$first": "$course" },
            "studyplans": {
                "$push": {
                    "semesterType": "$semester.type"
                }
            }
        }
    },
    {
        "$lookup": {
            "from": "teachers",
            "localField": "courseDocument.teachers",
            "foreignField": "_id",
            "as": "teachers"
        }
    },
     {
        "$addFields": {
            "courseDocument.studyplans": "$studyplans",
            "courseDocument.teachers": "$teachers"
        }
    },
    {
        "$replaceRoot": { "newRoot": "$courseDocument" }
    }
    ]))

    # replace ObjectId _id with string _id
    for course in courses:
        course['_id'] = str(course['_id'])
        for teacher in course['teachers']:
            teacher.pop('_id')
        if 'studyplans' in course:
            semesterType = None
            for studyplan in course['studyplans']:
                if studyplan['semesterType'] != 'year' and semesterType == None:
                    semesterType = studyplan['semesterType']
            if semesterType != None:
                course['semesterType'] = semesterType


    return jsonify(courses)

@app.route('/api/studyplans', methods=['GET'])
def studyplans():
    # List all studyplans with their semester
    studyplans = list(db.studyplans.aggregate([
        {
            "$lookup": {
                "from": "units",
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
        if 'promo' not in studyplan['unit'][0]:
            studyplan['promo'] = None
        else:
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
        schedule['course'].pop('teachers')
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

    if (type(selection) != list):
        return abort(400)

    if (len(selection) > 0 and type(selection[0]) != dict):
        return abort(400)

    # Convert selection to datetime ranges
    datetime_ranges = []
    for item in selection:
        start_time = item["start"].replace('Z', '+00:00')
        end_time = item["end"].replace('Z', '+00:00')
        start_datetime = datetime.fromisoformat(start_time) + timedelta(hours=2)
        end_datetime = datetime.fromisoformat(end_time) + timedelta(hours=2)
        datetime_ranges.append({"start": start_datetime, "end": end_datetime})

    # Find all rooms that are booked during the datetime ranges
    query_conditions = []
    for date_range in datetime_ranges:
        query_conditions.append({
        "$or": [
            {"start_datetime": {"$lt": date_range["end"]}, "end_datetime": {"$gt": date_range["start"]}},
            {"start_datetime": {"$gte": date_range["start"], "$lt": date_range["end"]}},
            {"start_datetime": {"$lte": date_range["start"]}, "end_datetime": {"$gte": date_range["end"]}}
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


    if  "teachers" in course:
        # Retrieve teacher details for each ID in the 'teachers' field
        teachers_details = list(db.teachers.find({'_id': {'$in': course['teachers']}}))

        # Replace or augment the 'teachers' field in the course document
        course['teachers'] = teachers_details
    
    # find the plannedin that contains this course and populate the studyplan, popule the semester of the studyplans
    studyplans = list(db.planned_in.aggregate([
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
            "as": "studyplan.semester"
        }
    },
    {
        "$unwind": "$studyplan.semester"
    },
    {
        "$group": {
            "_id": "$course_id",
            "studyplans": {
                "$push": {
                    "studyplan_id": "$studyplan._id",
                    "name": "$studyplan.name",
                    "semester": "$studyplan.semester"
                }
            }
        }
    },
    {
        "$project": {
            "_id": 0,
            "course_id": "$_id",
            "studyplans": 1
        }
    },
    ]))
    
    if studyplans != None and len(studyplans) > 0:
        course['studyplans'] = studyplans[0]['studyplans']
    else:
        studyplans = None

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
        schedule.pop('available')

    course['_id'] = str(course['_id'])
    if studyplans != None:
        for studyplan in course['studyplans']:
            studyplan['studyplan_id'] = str(studyplan['studyplan_id'])
            studyplan['semester'].pop('_id')

    
    for teacher in course['teachers']:
        teacher.pop('_id')
        teacher.pop('available')
    course['schedules'] = schedules
    course.pop('available')
  

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
                "from": "units",
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
        schedule['course'].pop('teachers')
    
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