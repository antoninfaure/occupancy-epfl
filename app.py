from flask import request, Flask, render_template, redirect, url_for, abort
from flask_pymongo  import PyMongo, MongoClient
import pickle 
from datetime import datetime, timedelta, time as dt_time
import numpy as np
from flask_wtf.csrf import CSRFProtect
import re
from copy import deepcopy
from bson.objectid import ObjectId
import time as t_time

app = Flask(__name__)
app.config.from_pyfile('config.py')
client = MongoClient(f"mongodb+srv://{app.config.get('DB_USER')}:{app.config.get('DB_PASSWORD')}@{app.config.get('DB_URL')}/?retryWrites=true&w=majority")
csrf = CSRFProtect(app)
csrf.init_app(app)

db = client[app.config.get('DB_NAME')]

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/', methods=['GET'])
def home():

    # List all rooms
    rooms = db.rooms.find({ "available": True })

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
                "course_id": "$_id",
                "name": 1,
                "code": 1,
                "credits": 1,
                "edu_url": 1
            }
        }
    ]))

    courses.extend(course_without_studyplan_with_schedules)

    # Create a basic timetable structure
    days_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6:'Sunday'}
    times = range(8, 20)
    week_length = 7
    timetable_template = dict()
    timetable_template['timetable'] = dict()
    timetable_template['dates'] = dict()

    for time in times:
        timetable_template['timetable'][f'{time}-{time+1}'] = dict()
        for day in days_mapping.values():
            timetable_template['timetable'][f'{time}-{time+1}'][day] = dict()

    # Find the next semester
    semester = db.semesters.find_one({ "available": True }, sort=[("end_date", 1)])
    
    # Generate timetables for the next semester
    start_date = (datetime.now() + timedelta(hours=2)).date()
    end_date = semester['end_date'].date()

    timetables = []

    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date
    while week_start < end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(week_length): 
            current_date = week_start + timedelta(days=day_offset)
            week_timetable['dates'][days_mapping[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }

            disabled = current_date < start_date
            for time in times:
                week_timetable['timetable'][f'{time}-{time+1}'][days_mapping[current_date.weekday()]] = {
                    'date': current_date,
                    'disabled': disabled,
                    'date_name': current_date.strftime('%d/%m/%Y')
                }
                
        timetables.append(week_timetable)
        week_start = week_start + timedelta(days=7)
    

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

    return render_template('index.html', studyplans=studyplans, courses=courses, rooms=rooms, timetables=timetables)

@app.route('/room/', methods=['GET'])
def room():
    name = request.args.get('name')
    if (name == None):
        return redirect(url_for('home')) 

    name = re.sub(r"(?![A-Za-z0-9\-\.])", "", name)
 
    room = db.rooms.find_one({'name': name, "available": True })
    if (room == None):
        return redirect(url_for('home'))



    # Create a basic timetable structure
    days_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6:'Sunday'}
    times = range(8, 20)
    week_length = 7
    timetable_template = dict()
    timetable_template['timetable'] = dict()
    timetable_template['dates'] = dict()

    for time in times:
        timetable_template['timetable'][f'{time}-{time+1}'] = dict()
        for i in range(week_length):
            day = days_mapping[i]
            timetable_template['timetable'][f'{time}-{time+1}'][day] = dict()


    timetables = []

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
    start_date = min([schedule['start_datetime'] for schedule in (course_schedules + event_schedules)]).date()

    # Get the latest booking end date
    end_date = max([schedule['end_datetime'] for schedule in (course_schedules + event_schedules)]).date()

    # Generate timetables for the date range
    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date

    while week_start <= end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(week_length):
            current_date = week_start + timedelta(days=day_offset)
            week_timetable['dates'][days_mapping[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }
            for time in times:
                time_key = f'{time}-{time+1}'
                day_key = days_mapping[current_date.weekday()]

                # Assign course schedules
                for schedule in course_schedules:
                    start_time = schedule['start_datetime'].time().hour
                    end_time = schedule['end_datetime'].time().hour
                    
                    # Check if the schedule corresponds to the current time and day
                    if (schedule['start_datetime'].date() == current_date 
                            and start_time == time):
                        duration = end_time - start_time
                        week_timetable['timetable'][time_key][day_key].update({
                            'label': schedule['label'],
                            'duration': duration,
                            'course': schedule['course'][0]
                        })

                        # Mark subsequent hours as 'skip' if the course spans multiple hours
                        for extra_hours in range(1, duration):
                            if time + extra_hours < max(times):
                                next_hour_key = f'{time+extra_hours}-{time+1+extra_hours}'
                                week_timetable['timetable'][next_hour_key][day_key] = {'skip': True}

                # Assign event schedules
                for schedule in event_schedules:
                    start_hour = schedule['start_datetime'].time().hour
                    end_hour = schedule['end_datetime'].time().hour

                    # Check if the schedule corresponds to the current time and day
                    if (schedule['start_datetime'].date() == current_date 
                            and start_hour == time):
                        duration = end_hour - start_hour
                        map_event_type = {
                            'event': 'Event',
                            'other': 'Other'
                        }

                        schedule_label = schedule['type'] if schedule['type'] in map_event_type else 'other'

                        week_timetable['timetable'][time_key][day_key].update({
                            'label': schedule_label,
                            'duration': duration,
                            'name': schedule['name'],
                            'unit': schedule['unit'][0]['code']
                        })

                        # Mark subsequent hours as 'skip' if the event spans multiple hours
                        for extra_hours in range(1, duration):
                            if time + extra_hours < max(times):
                                next_hour_key = f'{time+extra_hours}-{time+1+extra_hours}'
                                week_timetable['timetable'][next_hour_key][day_key] = {'skip': True}

        timetables.append(week_timetable)
        week_start += timedelta(days=7)

    return render_template('room.html', room=room, timetables=timetables)

@app.route('/find_free_rooms', methods=['POST'])
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
        start_time, end_time = map(int, item['time'].split('-'))
        date_obj = datetime.strptime(item['date'], "%Y-%m-%d")
        start_datetime = datetime(date_obj.year, date_obj.month, date_obj.day, start_time)
        end_datetime = datetime(date_obj.year, date_obj.month, date_obj.day, end_time)
        datetime_ranges.append({"start": start_datetime, "end": end_datetime})
       
    # Find all rooms that are booked during the datetime ranges
    query_conditions = []
    for date_range in datetime_ranges:
        query_conditions.append({
            "$and": [
                {"start_datetime": {"$lt": date_range["end"]}},
                {"end_datetime": {"$gt": date_range["start"]}}
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


@app.route('/course', methods=['GET'])
def find_course():
    code = request.args.get('code')
    course = db.courses.find_one({ 'code' : code, 'available': True})

    if (course == None):
        return abort(404)
    
    # find the plannedin that contains this course and populate the studyplan, then find the semester of the studyplan
    #  
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
  
    # Create a basic timetable structure
    days_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5:'Saturday', 6:'Sunday'}
    times = range(8, 20)
    timetable_template = dict()
    timetable_template['timetable'] = dict()
    timetable_template['dates'] = dict()


    # Generate timetables for the semester
    if (semester == None):
        start_date = datetime.now().date()
        if len(schedules) > 0:
            end_date = max([schedule['end_datetime'] for schedule in schedules]).date()
        else:
            end_date = start_date
        week_length = 7
    else:
        start_date = semester['start_date'].date()
        end_date = semester['end_date'].date()
        week_length = 5

    for time in times:
        timetable_template['timetable'][f'{time}-{time+1}'] = dict()
        for i in range(week_length):
            day = days_mapping[i]
            timetable_template['timetable'][f'{time}-{time+1}'][day] = dict()

    timetables = []

    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date

    while week_start <= end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(week_length):  # 5-day week
            current_date = week_start + timedelta(days=day_offset)
            week_timetable['dates'][days_mapping[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }
            for time in times:
                time_key = f'{time}-{time+1}'
                day_key = days_mapping[current_date.weekday()]

                if current_date < start_date:
                    week_timetable['timetable'][time_key][day_key] = {
                        'disabled': True,
                    }
                    continue
                
                if semester != None:
                    if 'skip_dates' in semester and current_date in semester['skip_dates']:
                        week_timetable['timetable'][time_key][day_key] = {
                            'disabled': True,
                        }
                        continue

                for schedule in schedules:
                    start_time = schedule['start_datetime'].time().hour
                    end_time = schedule['end_datetime'].time().hour
                                
                    # Check if the schedule corresponds to the current time and day
                    if (schedule['start_datetime'].date() == current_date and start_time == time):
                        duration = end_time - start_time
                        week_timetable['timetable'][time_key][day_key] = {
                            'label': schedule['label'],
                            'duration': duration,
                            'rooms': schedule['rooms']
                        }

                        # Mark subsequent hours as 'skip' if the booking spans multiple hours
                        for extra_hours in range(1, duration):
                            if time + extra_hours < max(times):
                                next_hour_key = f'{time+extra_hours}-{time+1+extra_hours}'
                                week_timetable['timetable'][next_hour_key][day_key] = {'skip': True}

        timetables.append(week_timetable)
        week_start = week_start + timedelta(days=7)

    return render_template('course.html', course=course, timetables=timetables)

@app.route('/find_studyplan', methods=['GET'])
def find_studyplan():
    studyplan_id = request.args.get('studyplan')

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
        return redirect(url_for('home'))
    
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

    def generate_week_timetable(week_start, all_schedules):
        days_mapping = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6:'Sunday'}
        times = range(8, 20)
        week_length = 5

        week_timetable = dict()
        week_timetable['timetable'] = dict()
        week_timetable['dates'] = dict()

        for time in times:
            week_timetable['timetable'][f'{time}-{time+1}'] = dict()
            for i in range(week_length):
                day = days_mapping[i]
                week_timetable['timetable'][f'{time}-{time+1}'][day] = []

        for day_offset in range(week_length):
            current_date = week_start + timedelta(days=day_offset)
            current_day = days_mapping[current_date.weekday()]

            week_timetable['dates'][days_mapping[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }

            # Filter schedules that are relevant to the current day and group them by (course, start hour, end hour)
            schedules_at_this_day = [b for b in all_schedules if b['start_datetime'].date() == current_date]

            # For each group, add to the timetable
            for schedule in schedules_at_this_day:
                course = schedule['course']
                rooms = schedule['rooms']
                label = schedule['label']

                start_hour = schedule['start_datetime'].hour
                end_hour = schedule['end_datetime'].hour
                duration = end_hour - start_hour

                week_timetable['timetable'][f'{start_hour}-{start_hour+1}'][current_day].append({
                    'course': course,
                    'rooms': rooms,
                    'rowspan': duration,
                    'label': label
                })
        
        
        

        # Adjust for continuous multi-hour courses
        for time in times:
            for i in range(week_length):
                day = days_mapping[i]
                slots = week_timetable['timetable'][f'{time}-{time+1}'][day]
                for slot in slots:
                    if 'rowspan' not in slot:
                        continue
                    if slot or slot['rowspan'] > 1:
                        for next_time in range(time + 1, time + slot['rowspan']):
                            week_timetable['timetable'][f'{next_time}-{next_time+1}'][day].append({'skip': True})

        # Find max colspan for each day
        for i in range(week_length):
            day = days_mapping[i]
            colspan = 1
            for time in times:
                slots = week_timetable['timetable'][f'{time}-{time+1}'][day]
                if len(slots) > colspan:
                    colspan = len(slots)
            week_timetable['dates'][day]['colspan'] = colspan

        # Adujst length of slots to match colspan
        for time in times:
            for i in range(week_length):
                day = days_mapping[i]
                slots = week_timetable['timetable'][f'{time}-{time+1}'][day]
                if len(slots) < week_timetable['dates'][day]['colspan']:
                    for _ in range(week_timetable['dates'][day]['colspan'] - len(slots)):
                        slots.append({})

        return week_timetable
    
    # Generate timetables for the entire semester
    timetables = []
    start_date = semester['start_date'].date()
    end_date = semester['end_date'].date()

    week_start = start_date - timedelta(days=start_date.weekday())
    while week_start < end_date:
        week_timetable = generate_week_timetable(week_start, schedules)
        timetables.append(week_timetable)
        
        week_start = week_start + timedelta(days=7)


    return render_template('semester.html', studyplan=studyplan, timetables=timetables, courses=courses_in_studyplan)

    

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('home'))
    
if __name__ == "__main__":
    app.run(debug=True)