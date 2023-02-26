import requests
from bs4 import BeautifulSoup
import pymongo
from pymongo import MongoClient
import numpy as np
import re
import pickle 
from urllib.parse import urlparse, parse_qs

def getAllCours():
    URL_ROOT = 'https://edu.epfl.ch/'
    shs = ['https://edu.epfl.ch/studyplan/fr/bachelor/programme-sciences-humaines-et-sociales/', 'https://edu.epfl.ch/studyplan/fr/master/programme-sciences-humaines-et-sociales/']
    page = requests.get(URL_ROOT)
    soup = BeautifulSoup(page.content, "html.parser")
    cards = soup.findAll("div", class_="card-title")
    annees = [card.find('a').get('href') for card in cards]
    courses = []
    for annee in annees:
        page = requests.get(URL_ROOT + annee)
        soup = BeautifulSoup(page.content, "html.parser")
        sections = [x.get('href') for x in soup.find('main').find('ul').findAll('a')]
        for section in sections:
            page = requests.get(URL_ROOT + section)
            soup = BeautifulSoup(page.content, "html.parser")
            for cours in soup.find('main').findAll('div', class_="cours-name"):
                if cours.find('a') != None:
                    courses.append(cours.find('a').get('href').split('/').pop())
    courses.remove('programme-sciences-humaines-et-sociales')
    for url in shs:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        for cours in soup.findAll("div", class_="cours-name"):
            if cours.find('a') != None:
                courses.append(cours.find('a').get('href').split('/').pop())
                
    return courses

def parseCours(url):
    page = requests.get(url)
    if (page.status_code == 404):
        print(url)
        return
        
    soup = BeautifulSoup(page.content, "html.parser")
    
    schedule = dict()
    title = soup.find('main').find('h1').text
    if (soup.find('div', class_="course-summary") == None):
        print(url)
    code = soup.find('div', class_="course-summary").findAll('p')[0].text.split('/')[0].strip()
    credits = int(re.findall(r'\d+', soup.find('div', class_="course-summary").findAll('p')[0].text.split('/')[1])[0])
    teachers = [(x.text, x.get('href')) for x in soup.find('div', class_="course-summary").findAll('p')[1].findAll('a')]

    semester = soup.find('div', class_="study-plans").findAll('div', class_="collapse-item")[0].findAll('li')[0].text.split(':')[1].strip()
    if (semester != 'Printemps' and semester != 'Automne'):
        semester = None
        
    if (semester == None):
        # Ecole doctorale
        #print(f'Ecole doctorale : {url}')
        schedule = dict()
        iframe_soup = BeautifulSoup(requests.get(soup.find("iframe").attrs['src']).content, "html.parser")
        if (iframe_soup.find('table') == None):
            #print(f'\033[91m SKIP (no schedule) \033[0m')
            return
        semester = 'Printemps'
        rows = iframe_soup.findAll('tr')
        creneaux = []
        for i, row in enumerate(rows):
            if (i == 0):
                continue
            if (row.find('th') != None):
                day = row.find('th').text.split('\xa0')[0][:2]
                if ('2023' not in row.find('th').text.split('\xa0')[1]):
                    year = row.find('th').text.split('\xa0')[1]
                    #print(f'\033[91m SKIP (not 2023 -> {year}) \033[0m')
                    day = None
                    continue
                if (int(row.find('th').text.split('\xa0')[1].split('.')[1]) > 5):
                    year = row.find('th').text.split('\xa0')[1]
                    #print(f'\033[91m SKIP (during summer -> {year}) \033[0m')
                    day = None
                    continue
            elif (row.get("class") != None and 'grisleger' in row.get("class") and day != None):
                time = [x.split(':')[0] for x in row.findAll('td')[0].text.split('-')]
                duration = int(time[1]) - int(time[0])
                time = f"{int(time[0])}-{int(time[0]) + 1}"
                rooms_found = [room.text for room in row.findAll('td')[1].findAll('a')]
                rooms = []
                for room in rooms_found:
                    if (room in rooms_map):
                        if (isinstance(rooms_map[room], list)):
                            rooms.append([x for x in rooms_map[room]])
                        else:
                            rooms.append(rooms_map[room])
                    elif (room not in rooms_filter):
                        rooms.append(room)
                label = row.findAll('td')[2].text
                if (label == 'L'):
                    label = 'cours'
                elif(label == 'E'):
                    label = 'exercice'
                elif(label == 'P'):
                    label = 'projet'
                else:
                    print(label)
                creneau = {
                    'day': day,
                    'time': time,
                    'label': label,
                    'rooms': rooms,
                    'duration': duration
                }
                if (len(rooms) > 0):
                    creneaux.append(creneau)
                creneau = {}
        if len(creneaux) == 0:
            #print(f'\033[91m SKIP (no creneaux) \033[0m')
            return
        for creneau in creneaux:
            day = creneau['day']
            time = creneau['time']
            if (time not in schedule):
                schedule[time] = dict()
            if (day not in schedule[time]):
                schedule[time][day] = {
                    'duration': creneau['duration'],
                    'rooms': creneau['rooms'],
                    'label': creneau['label']
                }
            elif (schedule[time][day]['duration'] == creneau['duration']):
                old_rooms = schedule[time][day]['rooms']
                new_rooms = creneau['rooms']
                schedule[time][day]['rooms'] = list(set(old_rooms + new_rooms))
        #print(f'\033[92m {schedule} \033[0m')

    else:
        # Not ecole doctorale
        if (soup.find("table", class_="semaineDeRef") != None):
            rows = soup.find("table", class_="semaineDeRef").findAll("tr")
            days = []
            for i, row in enumerate(rows):
                col = row.findAll('td')
                skip_days = 0
                for j, col in enumerate(col):
                    if (i == 0):
                        if (j > 0):
                            days.append(col.text)
                    else:
                        if (j == 0):
                            time = col.text
                        else:
                            day = days[j-1]
                            if (time in schedule):
                                if (day in schedule[time]):
                                    if ('skip' in schedule[time][day]):
                                        skip_days += 1
                            classes = col.get('class')
                            if (classes != None and "taken" in classes):
                                if (col.get('rowspan') == None):
                                    duration = 1
                                else:
                                    duration = int(col.get('rowspan'))
                                classes.remove('taken')
                                if (len(classes) != 0):
                                    label = classes[0]
                                    day = days[j-1 + skip_days]
                                    rooms_found = [room.text for room in col.findAll('a')]
                                    rooms = []
                                    for room in rooms_found:
                                        if (room in rooms_map):
                                            if (isinstance(rooms_map[room], list)):
                                                for x in rooms_map[room]:
                                                    rooms.append(x)
                                            else:
                                                rooms.append(rooms_map[room])
                                        elif (room not in rooms_filter):
                                            rooms.append(room)
                                    if (len(rooms) > 0):
                                        if (time not in schedule):
                                            schedule[time] = dict()
                                        schedule[time][day] = {
                                            'label': label,
                                            'duration': duration,
                                            'rooms': rooms
                                        }
                                        if (duration > 1):
                                            for k in range(duration):
                                                k_time = '-'.join(list(map(lambda x: str(int(x)+k), time.split('-'))))
                                                if (k_time not in schedule):
                                                    schedule[k_time] = dict()
                                                    schedule[k_time][day] = {
                                                        'skip': True
                                                    }
        if (len(schedule.keys()) == 0):
            print(f'\033[91m NO SCHEDULE ({code}) \033[0m')
            return


    
    course = {
        'name': title,
        'code': code,
        'credits': credits,
        'semester': semester,
        'teachers': teachers,
        'schedule': schedule
    }

    return course


def list_entities(data):

    # Get list of unique teachers
    teachers = sum([x['teachers'] for x in data], [])
    teachers = list(set(teachers))
    teachers = [{
        'name': x[0],
        'people_url': x[1]
    } for x in teachers]

    # Get list of unique rooms
    rooms = []
    for x in data:
        for time in x['schedule'].values():
            for day in time.values():
                rooms.append(day['rooms'])

    rooms = list(set(sum(rooms, [])))
    rooms = [{ 'name': room, "available": True } for room in rooms]

    # Get list of unique courses
    codes = []
    courses = []
    for course in data:
        if (course['code'] not in codes):
            courses.append({
                'name': course['name'],
                'code': course['code'],
                'credits': course['credits'],
                'semester': course['semester']
            })
            codes.append(course['code'])

    return rooms, teachers, courses

def save_entities_db(db, rooms, teachers, courses):
    for room in rooms:
        db.rooms.update_one({'name': room['name']}, {"$set": room}, upsert=True)
    for teacher in teachers:
        db.teachers.update_one({'name': teacher['name']}, {"$set": teacher}, upsert=True)
    for course in courses:
        db.courses.update_one({'code': course['code']}, {"$set": course}, upsert=True)


def list_relations(data):

    # Get list of unique teach_in
    teach_in = []
    for course in data:
        for teacher in course['teachers']:
            teach_in.append((
                course['code'],
                teacher[0]
            ))
    teach_in = list(set(teach_in))
    
    # Get list of unique booking
    booking = []
    for course in data:
        for time, row in course['schedule'].items():
            for day, creneau in row.items():
                if ('skip' not in creneau):
                    for room in creneau['rooms']:
                        booking.append({
                            'room': room,
                            'course': course['code'],
                            'label': creneau['label'],
                            'duration': creneau['duration'],
                            'time': time,
                            'day': day,
                            'semester': course['semester']
                        })
    
    return teach_in, booking


def update_relations_db(db, teach_in, booking):
    queried_rooms = db.rooms.find()
    queried_teachers = db.teachers.find()
    queried_courses = db.courses.find()

    map_room = dict()
    for room in queried_rooms:
        map_room[room['name']] = room['_id']

    map_teacher = dict()
    for teacher in queried_teachers:
        map_teacher[teacher['name']] = teacher['_id'] 

    map_course = dict()
    for course in queried_courses:
        map_course[course['code']] = course['_id']

    # Map the DB ids
    teach_in = [{
        'teacher': map_teacher[x[1]],
        'course': map_course[x[0]]
    } for x in teach_in]

    booking = [{
        **x,
        'room': map_room[x['room']],
        'course': map_course[x['course']],
    } for x in booking]

    # Insert in DB
    db.teach_in.drop()
    db.booking.drop()

    db.teach_in.insert_many(teach_in)
    db.booking.insert_many(booking)

def load_file(name):
    with open(name, 'rb') as handle:
        data = pickle.load(handle)
    return data

def DB_indices(db):
    try:
        db.rooms.create_index([("name", pymongo.ASCENDING)], name="room_name", unique=True)
        db.teachers.create_index([("name", pymongo.ASCENDING)], name="teacher_unique", unique=True)
        db.courses.create_index([("code", pymongo.ASCENDING)], name="course_unique", unique=True)
        db.teach_in.create_index([("teacher", pymongo.ASCENDING), ("course", pymongo.ASCENDING)], name="teach_in_unique", unique=True)
        db.booking.create_index([("room", pymongo.ASCENDING), ("time", pymongo.ASCENDING), ("day", pymongo.ASCENDING), ("semester", pymongo.ASCENDING)], name="booking_unique", unique=True)
        db.plans.create_index([("promo", pymongo.ASCENDING), ("course", pymongo.ASCENDING), ("section", pymongo.ASCENDING)], name="unique_plan", unique=True)
    except Exception as err:
        print(err)


def list_level_rooms(low, up, floor, max=1000):
    low1, low2 = low
    up1, up2 = up
    request_url = f"https://plan.epfl.ch/mapserv_proxy?ogcserver=source+for+image%2Fpng&cache_version=9fe661ce469e4692b9e402b22d8cb420&floor={floor}"
    xml = f'<GetFeature xmlns="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="GML3" maxFeatures="{max}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd"><Query typeName="feature:batiments_wmsquery" srsName="EPSG:2056" xmlns:feature="http://mapserver.gis.umn.edu/mapserver"><Filter xmlns="http://www.opengis.net/ogc"><BBOX><PropertyName>the_geom</PropertyName><Envelope xmlns="http://www.opengis.net/gml" srsName="EPSG:2056"><lowerCorner>{low1} {low2}</lowerCorner><upperCorner>{up1} {up2}</upperCorner></Envelope></BBOX></Filter></Query></GetFeature>'

    r = requests.post(request_url, data=xml)
    room_xml = BeautifulSoup(r.text, 'xml')
    if (room_xml.find('gml:Null') != None):
        return None
    return room_xml.findAll('gml:featureMember')

def parse_all_levels():
    rooms = []
    for level in range(-3, 6):
        level_rooms = list_level_rooms((2533565.4081416847, 1152107.9784703811), (2532650.4135850836, 1152685.3502971812), level, max=5000)
        if (level_rooms and len(level_rooms) > 0):
            rooms += level_rooms
    return rooms

def parse_room(room_xml):
    room_name = BeautifulSoup(room_xml.find('ms:room_abr_link').text, 'html.parser').find('div', class_="room").text.replace(" ", "")
    room_type = room_xml.find('ms:room_uti_a').text
    return { 'name': room_name, 'type': room_type }

def parse_all_rooms(rooms_xml):
    rooms_parsed = []
    types = []
    for room_xml in rooms_xml:
        room = parse_room(room_xml)
        if (room == None):
            continue
        if (room not in rooms):
            rooms_parsed.append(room)
        if (room['type'] not in types):
            types.append(room['type'])
    return rooms_parsed, types

def update_rooms_type(db, rooms_parsed):
    query_rooms = db.rooms.find()
    for room in query_rooms:
        room_name = room['name']
        found = False
        for x in rooms_parsed:
            if (x['name'] == room_name):
                db.rooms.update_one({'name': x['name']}, {"$set": {
                    'type': x['type']
                }}, upsert=True)
                found = True
                break
        # If the room is not found in the parsed list, print name
        if (found == False):
            print(f'{room["name"]}')

def list_plans():
    URL_BA = "https://edu.epfl.ch/studyplan/fr/bachelor/"
    URL_ROOT = 'https://edu.epfl.ch/'

    # Find all BA study plans for each section and all courses in them
    page = requests.get(URL_BA)
    soup = BeautifulSoup(page.content, "html.parser")
    sections = [x.get('href') for x in soup.find('main').find('ul').findAll('a')]
    plans_etudes = []
    for section in sections:
        page = requests.get(URL_ROOT + section)
        soup = BeautifulSoup(page.content, "html.parser")
        section_name = ' '.join(soup.find('main').find('header').find('h2').text.split(' ')[:-1])
        for cours in soup.find('main').findAll('div', class_="line"):
            if (cours != None):
                code = cours.find('div', class_='cours-info').text.split('/')[0].replace(" ", "")
                if (code != ''):
                    for sem in cours.findAll('div', class_='bachlor'):
                        issemester = False
                        for cep in sem.findAll('div', class_='cep'):
                            if (cep.text != '-'):
                                issemester = True
                        if (issemester == True):
                            semester = sem.attrs['data-title']
                    if (section_name in map_section):
                        plans_etudes.append({
                            "code": code,
                            "promo": map_semester[semester],
                            "section": map_section[section_name]
                        })
                    else:
                        print(section_name)
    return plans_etudes

def update_plans_db(db, plans_etudes):
    # Update the plans in DB
    for course in plans_etudes:
        course_db = db.courses.find_one({ 'code' : course['code']})
        if (course_db != None):
            db.plans.update_one({'section': course['section'], 'course': course_db['_id'], 'promo': course['promo']}, {'$set' : {'section': course['section'], 'course': course_db['_id'], 'promo': course['promo']}}, upsert=True)
        else:
            # If the course in not in our DB, print course
            print(course)