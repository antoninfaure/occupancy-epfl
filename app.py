from flask import request, Flask, render_template, redirect, url_for, abort
from flask_pymongo  import PyMongo, MongoClient
import pickle 
from datetime import datetime, timedelta, time as dt_time
import numpy as np
from flask_wtf.csrf import CSRFProtect
import re
from copy import deepcopy
from bson.objectid import ObjectId

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
    rooms = db.rooms.find({ "available": True })
    pipeline = [
        {
            "$match": {
                "available": True
            }
        },
        {
            "$lookup": {
                "from": "planned_in",
                "localField": "_id",
                "foreignField": "course_id",
                "as": "plannedInData"
            }
        },
        {
            "$unwind": "$plannedInData"
        },
        {
            "$lookup": {
                "from": "studyplans",
                "localField": "plannedInData.studyplan_id",
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
                "_id": "$_id",
                "name": { "$first": "$name" },
                "code": { "$first": "$code" },
                "credits": { "$first": "$credits" },
                "semester": { "$first": "$semester" }
            }
        }
    ]

    courses = list(db.courses.aggregate(pipeline))

    days_mapping = {
        0: 'Lu',
        1: 'Ma',
        2: 'Me',
        3: 'Je',
        4: 'Ve'
    }

    times = range(8, 20)
    timetable_template = dict()

    for time in times:
        timetable_template[f'{time}-{time+1}'] = dict()
        for day in days_mapping.values():
            timetable_template[f'{time}-{time+1}'][day] = dict()

    # Find the next semester
    semester = db.semesters.find_one({ "available": True }, sort=[("end_date", 1)])
    
    # Generate timetables for the next semester
    start_date = datetime.now().date()
    end_date = semester['end_date'].date()

    timetables = []

    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date
    while week_start < end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(5):  # We are considering a 5-day week
            current_date = week_start + timedelta(days=day_offset)
            disabled = current_date < start_date
            for time in times:
                week_timetable[f'{time}-{time+1}'][days_mapping[current_date.weekday()]] = {
                    'date': current_date,
                    'disabled': disabled,
                    'date_name': current_date.strftime('%d/%m/%Y')
                }
                
        timetables.append(week_timetable)
        week_start = week_start + timedelta(days=7)
    
    pipeline = [
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
                "from": "semesters",  # Assuming the name of your semester collection is 'semesters'
                "localField": "semester_id",  # Assuming the field in studyplans referring to semester is 'semester_id'
                "foreignField": "_id",
                "as": "semester"
            }
        },
        {
            "$match": {
                "available": True
            }
        }
    ]

    studyplans = list(db.studyplans.aggregate(pipeline))

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
    
    # Find the next semester
    semester = db.semesters.find_one({ "available": True }, sort=[("end_date", 1)])

    # Create a basic timetable structure
    days_mapping = {0: 'Lu', 1: 'Ma', 2: 'Me', 3: 'Je', 4: 'Ve'}
    times = range(8, 20)
    timetable_template = dict()
    timetable_template['timetable'] = dict()
    timetable_template['dates'] = dict()

    for time in times:
        timetable_template['timetable'][f'{time}-{time+1}'] = dict()
        for day in days_mapping.values():
            timetable_template['timetable'][f'{time}-{time+1}'][day] = dict()

    # Generate timetables for the semester
    start_date = datetime.now().date()
    end_date = semester['end_date'].date()
    timetables = []

    # Convert the date objects to datetime for MongoDB comparison
    start_datetime = datetime.combine(start_date, dt_time(0, 0))  # start of the day
    end_datetime = datetime.combine(end_date, dt_time(23, 59, 59))  # end of the day


    try:
        pipeline = [
            {
                "$match": {
                    'room_id': room['_id'],
                    'start_datetime': { '$gte': start_datetime },
                    'end_datetime': { '$lte': end_datetime }
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
        ]

        schedules = list(db.booking.aggregate(pipeline))
    except Exception as e:
        print(e)

    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date

    while week_start <= end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(5):  # 5-day week
            current_date = week_start + timedelta(days=day_offset)
            week_timetable['dates'][days_mapping[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }
            for time in times:
                time_key = f'{time}-{time+1}'
                day_key = days_mapping[current_date.weekday()]

                # Assign course schedules
                for schedule in schedules:
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
    
    # Find all booked rooms
    booked_rooms = db.booking.find({"$or": query_conditions})
    booked_room_ids = [room["room_id"] for room in booked_rooms]

    # Find available rooms that are not in booked_room_ids
    free_rooms = list(db.rooms.find({"available": True, "_id": {"$nin": booked_room_ids}}))

    rooms_names = [{'name': x['name'], 'type': x['type']} for x in list(free_rooms)]

    print("results")

    return rooms_names

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
    ]))[0]

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

    # Find all booking
    # Build the aggregation pipeline
    pipeline = [
        {
            "$match": {
                'course_id': {'$in': list(map(lambda x: x['_id'], courses_in_studyplan))},
                'available': True
            }
        },
        {
            "$lookup": {
                "from": "rooms",
                "localField": "room_id",
                "foreignField": "_id",
                "as": "room"
            }
        },
        {
            "$unwind": "$room"
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
        }
    ]

    # Get the bookings with populated room and course info
    bookings = list(db.booking.aggregate(pipeline))

    def generate_week_timetable(week_start, all_bookings):
        days = ['Lu', 'Ma', 'Me', 'Je', 'Ve']
        times = range(8, 20)

        week_timetable = dict()
        
        week_timetable['timetable'] = {f'{time}-{time+1}': {day: [] for day in days} for time in times}
        week_timetable['dates'] = {day: date.strftime('%d/%m/%Y') for day, date in zip(days, [week_start + timedelta(days=day_offset) for day_offset in range(5)])}

        for day_offset in range(5):  # Considering a 5-day week
            current_date = week_start + timedelta(days=day_offset)
            
            for time in times:
                hour_start = datetime.combine(current_date, dt_time(time, 0))
                hour_end = datetime.combine(current_date, dt_time(time+1, 0))

                # Filter bookings that are relevant to the current hour slot
                bookings_at_this_time = [b for b in all_bookings if b['start_datetime'] < hour_end and b['end_datetime'] > hour_start]

                for booking in bookings_at_this_time:
                    start_hour = booking['start_datetime'].hour
                    end_hour = booking['end_datetime'].hour
                    duration = end_hour - start_hour
                    
                    week_timetable['timetable'][f'{start_hour}-{start_hour+1}'][days[day_offset]].append({
                        'course': booking['course'],
                        'room': booking['room'],
                        'rowspan': duration,
                        'label': booking['label']
                    })

        # Adjust for continuous multi-hour courses
        for time in times:
            for day in days:
                slots = week_timetable['timetable'][f'{time}-{time+1}'][day]
                for slot in slots:
                    if 'rowspan' not in slot:
                        continue
                    if slot or slot['rowspan'] > 1:
                        for next_time in range(time + 1, time + slot['rowspan']):
                            week_timetable['timetable'][f'{next_time}-{next_time+1}'][day].append({'skip': True})

        return week_timetable
    
    # Generate timetables for the entire semester
    timetables = []
    start_date = semester['start_date'].date()
    end_date = semester['end_date'].date()

    week_start = start_date - timedelta(days=start_date.weekday())
    while week_start < end_date:
        week_timetable = generate_week_timetable(week_start, bookings)
        timetables.append(week_timetable)
        
        week_start = week_start + timedelta(days=7)


    return render_template('semester.html', studyplan=studyplan, timetables=timetables)

@app.route('/course', methods=['GET'])
def find_course():
    code = request.args.get('code')
    course = list(db.courses.find({ 'code' : code, 'available': True}))[0]
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
    ]))[0]

    if (semester == None):
        return redirect(url_for('home'))
    
    semester = semester['semester']

    bookings = list(db.booking.aggregate([
        {
            "$match": {
                'course_id': course['_id'],
                'available': True
            }
        },
        {
            "$lookup": {
                "from": "rooms",
                "localField": "room_id",
                "foreignField": "_id",
                "as": "room"
            }
        },
        {
            "$unwind": "$room"
        }
    ]))
    
    # Create a basic timetable structure
    days_mapping = {0: 'Lu', 1: 'Ma', 2: 'Me', 3: 'Je', 4: 'Ve'}
    days_mapping_name = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi'}
    times = range(8, 20)
    timetable_template = dict()
    timetable_template['timetable'] = dict()
    timetable_template['dates'] = dict()

    for time in times:
        timetable_template['timetable'][f'{time}-{time+1}'] = dict()
        for day in days_mapping.values():
            timetable_template['timetable'][f'{time}-{time+1}'][day] = dict()

    # Generate timetables for the semester
    start_date = datetime.now().date()
    end_date = semester['end_date'].date()
    timetables = []

    week_start_date = start_date - timedelta(days=start_date.weekday())
    week_start = week_start_date

    while week_start <= end_date:
        week_timetable = deepcopy(timetable_template)
        for day_offset in range(5):  # 5-day week
            current_date = week_start + timedelta(days=day_offset)
            week_timetable['dates'][days_mapping_name[current_date.weekday()]] = {
                'date_name': current_date.strftime('%d/%m/%Y')
            }
            for time in times:
                time_key = f'{time}-{time+1}'
                day_key = days_mapping[current_date.weekday()]

                for schedule in bookings:
                    start_time = schedule['start_datetime'].time().hour
                    end_time = schedule['end_datetime'].time().hour
                                
                    # Check if the schedule corresponds to the current time and day
                    if (schedule['start_datetime'].date() == current_date and start_time == time):
                        duration = end_time - start_time
                        if 'rooms' not in week_timetable['timetable'][time_key][day_key]:
                            week_timetable['timetable'][time_key][day_key].update({
                                'label': schedule['label'],
                                'duration': duration,
                                'rooms': [schedule['room']['name']]  # initiate with a list containing the current room name
                            })
                        else:
                            # append the room name if there is already an entry for this time slot and day
                            week_timetable['timetable'][time_key][day_key]['rooms'].append(schedule['room']['name'])

                        # Mark subsequent hours as 'skip' if the booking spans multiple hours
                        for extra_hours in range(1, duration):
                            if time + extra_hours < max(times):
                                next_hour_key = f'{time+extra_hours}-{time+1+extra_hours}'
                                week_timetable['timetable'][next_hour_key][day_key] = {'skip': True}

        timetables.append(week_timetable)
        week_start = week_start + timedelta(days=7)

    return render_template('course.html', course=course, timetables=timetables)
    

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('home'))
    
if __name__ == "__main__":
    app.run(debug=True)