from flask import request, Flask, render_template, redirect, url_for, abort
from flask_pymongo  import PyMongo, MongoClient
import pickle 
from datetime import datetime
import numpy as np
from flask_wtf.csrf import CSRFProtect
import re

app = Flask(__name__)
app.config.from_pyfile('config.py')
client = MongoClient(f"mongodb+srv://{app.config['DB_USER']}:{app.config['DB_PASSWORD']}@{app.config['DB_URL']}/?retryWrites=true&w=majority")
csrf = CSRFProtect(app)
csrf.init_app(app)

db = client[app.config['DB_NAME']]

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.route('/', methods=['GET'])
def home():
    rooms = db.rooms.find()
    days = ['Lu', 'Ma', 'Me', 'Je', 'Ve']
    times = range(8, 20)
    timetable = dict()

    for i, time in enumerate(times):
        timetable[f'{time}-{time+1}'] = dict()
        for j, day in enumerate(days):
            timetable[f'{time}-{time+1}'][day] = dict()

    return render_template('index.html', rooms=rooms, timetable=timetable)

@app.route('/room/', methods=['GET'])
def room():
    name = request.args.get('name')
    if (name == None):
        return redirect(url_for('home')) 

    name = re.sub(r"(?![A-Za-z0-9\-\.])", "", name)
 
    room = db.rooms.find_one({'name': name})
    if (room == None):
        return redirect(url_for('home'))

    schedules = list(db.booking.find({
        'room': room['_id'],
        'semester': 'Printemps'
    }))

    for schedule in schedules:
        course = db.courses.find_one({ '_id': schedule['course'] })
        schedule['course'] = course
    days = ['Lu', 'Ma', 'Me', 'Je', 'Ve']
    times = range(8, 20)
    timetable = dict()

    for i, time in enumerate(times):
        timetable[f'{time}-{time+1}'] = dict()
        for j, day in enumerate(days):
            timetable[f'{time}-{time+1}'][day] = dict()
            for schedule in schedules:
                if (schedule['day'] == day and schedule['time'] == f'{time}-{time+1}'):
                    timetable[f'{time}-{time+1}'][day] = schedule
            for k in range(i):
                k_time = f'{times[k]}-{times[k]+1}'
                if (len(timetable[k_time][day]) > 0):
                    if ('duration' in timetable[k_time][day] and timetable[k_time][day]['duration'] > i - k):
                        timetable[f'{time}-{time+1}'][day] = {'skip': True}
    
    return render_template('room.html', room=room, timetable=timetable)

@app.route('/find_free_rooms', methods=['POST'])
def find_free_rooms():
    selection = request.json
    if (selection == None):
        return abort(400)

    if (type(selection) != list):
        return abort(400)

    if (len(selection) > 0 and type(selection[0]) != dict):
        return abort(400)

    booking = list(db.booking.find({'semester': 'Printemps'}))
    
    list_rooms = []
    booked_rooms = []
    for schedule in booking:
        room = schedule['room']
        time = schedule['time']
        day = schedule['day']
        if (room not in list_rooms):
            list_rooms.append(room)

        for select in selection:
            for k in range(schedule['duration']):
                k_time = "-".join([str(int(x) + k) for x in time.split('-')])
                if (k_time == select['time'] and day == select['day']):
                    if (room not in booked_rooms):
                        booked_rooms.append(room)
    available_rooms = list(set(list_rooms) - set(booked_rooms))

    rooms = db.rooms.find({ '_id': { '$in': available_rooms}})

    rooms_name = [{'name': x['name'], 'type': x['type']} for x in list(rooms)]

    return rooms_name

@app.route('/find_semester', methods=['GET'])
def find_semester():
    section = request.args.get('section')
    promo = request.args.get('semester')
    courses_ids = list(map(lambda x: x['course'], list(db.plans.find({ 'section': section, 'promo': promo }))))

    courses = list(db.courses.find({ '_id' : { '$in' : courses_ids} }))

    if (len(courses) == 0):
        return redirect(url_for('home'))

    bookings = list(db.booking.find({ 'course': {'$in' : list(map(lambda x: x['_id'], courses))}}))

    for schedule in bookings:
        course = db.courses.find_one({ '_id': schedule['course'] })
        schedule['course'] = course
        room = db.rooms.find_one({ '_id': schedule['room'] })
        schedule['room'] = room

    days = ['Lu', 'Ma', 'Me', 'Je', 'Ve']
    times = range(8, 20)
    timetable = dict()
    colspan = {'Lu' : 1, 'Ma' : 1, 'Me' : 1, 'Je' : 1, 'Ve' : 1}

    for i, time in enumerate(times):
        timetable[f'{time}-{time+1}'] = dict()
        for j, day in enumerate(days):
            timetable[f'{time}-{time+1}'][day] = []
            for schedule in bookings:
                if (schedule['day'] == day and schedule['time'] == f'{time}-{time+1}'):
                    solved = False
                    # List all slots at that time-day
                    for i_slot, slot in enumerate(timetable[f'{time}-{time+1}'][day]):
                        # If the same course then add room to list
                        if ('course' in slot and schedule['course']['code'] == slot['course']['code']):
                            timetable[f'{time}-{time+1}'][day][i_slot]['rooms'].append(schedule['room']['name'])
                            solved = True

                    # If conflict not solved then append new slot
                    if (solved == False):
                        timetable[f'{time}-{time+1}'][day].append({
                                'course' : {
                                    'code': schedule['course']['code'],
                                    'name': schedule['course']['name']
                                },
                                'time': schedule['time'],
                                'day': schedule['day'],
                                'label': schedule['label'],
                                'duration': schedule['duration'],
                                'rooms': [schedule['room']['name']],
                                'colspan' : 1
                            })

            for k in range(i):
                k_time = f'{times[k]}-{times[k]+1}'
                if (len(timetable[k_time][day]) > 0):
                    for slot in timetable[k_time][day]:
                        if ('duration' in slot and slot['duration'] > i - k):
                            timetable[f'{time}-{time+1}'][day].append({'skip': True})

    # Find max colspan per day
    for time in times:
        for day in days:
            cols = len(timetable[f'{time}-{time+1}'][day])
            if (cols > colspan[day]):
                colspan[day] = cols
    
    # Fill colspan
    for time in times:
        for day in days:
            cols = len(timetable[f'{time}-{time+1}'][day])
            if (day == 'Lu'):
                print(f'{time}-{time+1} / {day} = {cols}')
            if (cols > 0 and cols < colspan[day]):
                max_cols = cols
                if ('skip' not in timetable[f'{time}-{time+1}'][day][0]):
                    for k in range(timetable[f'{time}-{time+1}'][day][0]['duration']):
                        if (len(timetable[f'{k+time}-{k+time+1}'][day]) > max_cols):
                            max_cols = len(timetable[f'{k+time}-{k+time+1}'][day])
                timetable[f'{time}-{time+1}'][day][0]['colspan'] = colspan[day] - max_cols + 1

    return render_template('semester.html', colspan=colspan, timetable=timetable)

@app.route('/course', methods=['GET'])
def find_course():
    code = request.args.get('code')
    course = list(db.courses.find({ 'code' : code}))[0]
    bookings = list(db.booking.find({ 'course' : course['_id']}))
    for i, schedule in enumerate(bookings):
        room = db.rooms.find_one({ '_id' : schedule['room']})
        bookings[i]['room'] = room

    days = ['Lu', 'Ma', 'Me', 'Je', 'Ve']
    times = range(8, 20)
    timetable = dict()

    for i, time in enumerate(times):
        timetable[f'{time}-{time+1}'] = dict()
        for j, day in enumerate(days):
            timetable[f'{time}-{time+1}'][day] = dict()
            for schedule in bookings:
                if (schedule['day'] == day and schedule['time'] == f'{time}-{time+1}'):
                    if ('rooms' in timetable[f'{time}-{time+1}'][day]):
                        timetable[f'{time}-{time+1}'][day]['rooms'].append(schedule['room']['name'])
                    else:
                        timetable[f'{time}-{time+1}'][day] = {
                                'time': schedule['time'],
                                'day': schedule['day'],
                                'label': schedule['label'],
                                'duration': schedule['duration'],
                                'rooms': [schedule['room']['name']],
                            }

            for k in range(i):
                k_time = f'{times[k]}-{times[k]+1}'
                if (len(timetable[k_time][day]) > 0):
                    if ('duration' in timetable[k_time][day] and timetable[k_time][day]['duration'] > i - k):
                        timetable[f'{time}-{time+1}'][day] = {'skip': True}
    return render_template('course.html', course=course, timetable=timetable)
    

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('home'))
    
if __name__ == "__main__":
    app.run(debug=True)