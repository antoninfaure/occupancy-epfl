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

    name = re.sub(r"[^a-zA-Z0-9 ]", "", name)

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

    rooms_name = [x['name'] for x in list(rooms)]

    return rooms_name

@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('home'))
    
if __name__ == "__main__":
    app.run(debug=True)