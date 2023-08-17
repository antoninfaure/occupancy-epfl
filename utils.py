import requests
from bs4 import BeautifulSoup
import re
from config import *
from datetime import datetime, timedelta
from tqdm import tqdm

### GET ALL COURSES URLS ###
def getAllCoursesUrl():
    URL_ROOT = 'https://edu.epfl.ch/'
    shs = ['https://edu.epfl.ch/studyplan/fr/bachelor/programme-sciences-humaines-et-sociales/', 'https://edu.epfl.ch/studyplan/fr/master/programme-sciences-humaines-et-sociales/']
    page = requests.get(URL_ROOT)
    soup = BeautifulSoup(page.content, "html.parser")
    cards = soup.findAll("div", class_="card-title")
    promos = [card.find('a').get('href') for card in cards]
    courses_url = []
    courses_names = []
    for promo in tqdm(promos):
        page = requests.get(URL_ROOT + promo)
        soup = BeautifulSoup(page.content, "html.parser")
        sections = [x.get('href') for x in soup.find('main').find('ul').findAll('a')]
        for section in sections:
            page = requests.get(URL_ROOT + section)
            soup = BeautifulSoup(page.content, "html.parser")
            for course in soup.find('main').findAll('div', class_="cours-name"):
                if course.find('a') != None:
                    course_url = course.find('a').get('href')
                    course_name = course_url.split('/').pop()
                    if 'programme-sciences-humaines-et-sociales' not in course_url and course_name not in courses_names:
                        courses_url.append(course_url)
                        courses_names.append(course_name)

    # Add SHS courses
    for url in shs:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        for course in soup.findAll("div", class_="cours-name"):
            if course.find('a') != None:
                course_url = course.find('a').get('href')
                course_name = course_url.split('/').pop()
                if course_name not in courses_names:
                    courses_url.append(course_url)
                    courses_names.append(course_name)
                
    return courses_url

### PARSE COURSE ###
def parseCourse(url):
    page = requests.get(url)
    if (page.status_code == 404):
        print(url)
        return
        
    soup = BeautifulSoup(page.content, "html.parser")
    
    title = soup.find('main').find('h1').text
    if (soup.find('div', class_="course-summary") == None):
        print(url)
    code = soup.find('div', class_="course-summary").findAll('p')[0].text.split('/')[0].strip()
    credits = int(re.findall(r'\d+', soup.find('div', class_="course-summary").findAll('p')[0].text.split('/')[1])[0])
    teachers = [(x.text, x.get('href')) for x in soup.find('div', class_="course-summary").findAll('p')[1].findAll('a')]

    semester = soup.find('div', class_="study-plans").findAll('div', class_="collapse-item")[0].findAll('li')[0].text.split(':')[1].strip()

    if (semester != 'Printemps' and semester != 'Automne'):
        semester = None
        schedule = parseScheduleEcoleDoctorale(soup)
        if schedule != None:
            semester = 'ecole_doctorale'
        #if schedule == None:
            #print(f'\033[91m NO SCHEDULE ({url}) \033[0m')
    else:
        schedule = parseSchedule(soup)
    
    course = {
        'name': title,
        'code': code,
        'credits': credits,
        'semester': semester,
        'teachers': teachers,
        'schedule': schedule,
        'edu_url': url
    }

    return course

### PARSE SCHEDULE DOCTORAL SCHOOL ###
def parseScheduleEcoleDoctorale(soup):
    # Ecole doctorale
    schedule = dict()

    iframe_soup = BeautifulSoup(requests.get(soup.find("iframe").attrs['src']).content, "html.parser")
    if (iframe_soup.find('table') == None):
        #print(f'\033[91m SKIP (no schedule) \033[0m')
        return None
    
    rows = iframe_soup.findAll('tr')
    creneaux = []
    
    for i, row in enumerate(rows):
        if (i == 0):
            continue
        if (row.find('th') != None):
            # find a dd.mm.yyyy date
            date = re.findall(r'\d{2}.\d{2}.\d{4}', row.find('th').text)
            if (len(date) > 0):
                date = datetime.strptime(date[0], '%d.%m.%Y')
        elif (row.get("class") != None and 'grisleger' in row.get("class") and date != None):
            time = [x.split(':')[0] for x in row.findAll('td')[0].text.split('-')]
            
            start_hour = int(time[0])
            duration = int(time[1]) - int(time[0])
        
            rooms_found = [room.text for room in row.findAll('td')[1].findAll('a')]

            rooms = []
            for room in rooms_found:
                if (room in MAP_ROOMS):
                    if (isinstance(MAP_ROOMS[room], list)):
                        rooms.append([x for x in MAP_ROOMS[room]])
                    else:
                        rooms.append(MAP_ROOMS[room])
                elif (room not in ROOMS_FILTER):
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
                'start_hour': start_hour,
                'duration': duration,
                'label': label,
                'rooms': rooms,
                'date': date
            }
            if (len(rooms) > 0):
                creneaux.append(creneau)
            creneau = {}

    if len(creneaux) == 0:
        #print(f'\033[91m SKIP (no creneaux) \033[0m')
        return None
    
    schedule = []
    for creneau in creneaux:
        found = False
        for i, s in enumerate(schedule):
            if (s['start_hour'] == creneau['start_hour'] and s['duration'] == creneau['duration'] and s['label'] == creneau['label'] and s['date'] == creneau['date']):
                schedule[i]['rooms'] = schedule[i]['rooms'] + creneau['rooms']
                found = True
                break
        if (not found):
            schedule.append(creneau)    

    return schedule

### PARSE SCHEDULE ###
def parseSchedule(soup):
    # Not ecole doctorale
    
    schedule = dict()

    if (soup.find("table", class_="semaineDeRef") == None):
        return None
    
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
                                if (room in MAP_ROOMS):
                                    if (isinstance(MAP_ROOMS[room], list)):
                                        for x in MAP_ROOMS[room]:
                                            rooms.append(x)
                                    else:
                                        rooms.append(MAP_ROOMS[room])
                                elif (room not in ROOMS_FILTER):
                                    rooms.append(room)
                            
                            if (time not in schedule):
                                schedule[time] = dict()
                            schedule[time][day] = {
                                'label': label,
                                'duration': duration,
                                'rooms': rooms
                            }
                            # Check if there is a skip to add on the day column
                            if (duration > 1):
                                for k in range(duration):
                                    k_time = '-'.join(list(map(lambda x: str(int(x)+k), time.split('-'))))
                                    if (k_time not in schedule):
                                        schedule[k_time] = dict()
                                        schedule[k_time][day] = {
                                            'skip': True
                                        }
                            
    if (len(schedule.keys()) == 0):
        return None
    
    return schedule


### CREATE NEW SEMESTER ###
def create_new_semester(db, **kwargs):
    name = kwargs.get("name") or None
    start_date = kwargs.get("start_date") or None
    end_date = kwargs.get("end_date") or None
    type = kwargs.get("type") or None
    available = kwargs.get("available") or False
    
    try:
        db.semesters.insert_one({
            "name": name,
            "start_date": start_date,
            "end_date": end_date,
            "type": type,
            "available": available
       })
    except Exception as e:
        print(e)

### CREATE COURSES ###
def create_courses(db, courses):
    '''
        Create courses in the db
        Input:
            - courses: a list of courses to create
        Output:
            - None
    '''
    db_courses_codes = [course.get('code') for course in db.courses.find()]
    
    new_courses = []
    for course in tqdm(courses, total=len(courses)):
        if (course.get("code") in db_courses_codes):
            continue
        new_courses.append({
            "code": course.get("code"),
            "name": course.get("name"),
            "credits": course.get("credits"),
            "edu_url": course.get("edu_url"),
            "available": True
        })

    if (len(new_courses) == 0):
        return
    
    try:
        db.courses.insert_many(new_courses)
    except Exception as e:
        print(e)

    return


### FILTER DUPLICATES COURSES ###
def filter_duplicates_courses(courses):
    '''
        Filter duplicates courses
        Input:
            - courses: a list of courses
        Output:
            - filtered_courses: a list of courses without duplicates
    '''
    filtered_courses = []
    filtered_courses_codes = []
    for course in courses:
        if (course.get("code") not in filtered_courses_codes):
            filtered_courses_codes.append(course.get("code"))
            filtered_courses.append(course)
    return filtered_courses


### CREATE TEACHERS ###
def create_teachers(db, courses):
    '''
        Create teachers in the db
        Input:
            - courses: a list of courses
        Output:
            - None
    '''
    db_teachers = list(db.teachers.find({
        "available": True
    }))

    new_teachers = []
    for course in tqdm(courses, total=len(courses)):
        for teacher in course.get("teachers"):
            found = False
            for db_teacher in db_teachers:
                if (db_teacher.get("name") == teacher[0]):
                    found = True
                    break
            
            for new_teacher in new_teachers:
                if (new_teacher.get("name") == teacher[0]):
                    found = True
                    break

            if (found == True):
                continue

            new_teachers.append({
                "name": teacher[0],
                "people_url": teacher[1],
                "available": True
            })

    if (len(new_teachers) == 0):
        return
    
    try:
        db.teachers.insert_many(new_teachers)
    except Exception as e:
        print(e)

    return

### CREATE TEACH IN ###
def create_teach_in(db, courses):
    '''
        Create teach_in in the db
        Input:
            - courses: a list of courses to create
        Output:
            - None
    '''
    db_teach_in = list(db.teach_in.find({
        "available": True
    }))

    new_teach_in = []
    for course in tqdm(courses):
        for teacher in course.get("teachers"):
            db_teacher = db.teachers.find_one({"name": teacher[0]})
            if (db_teacher is None):
                print("Teacher not found in db")
                continue

            db_course = db.courses.find_one({"code": course.get("code")})
            if (db_course is None):
                print("Course not found in db")
                continue

            found = False
            for db_teach in db_teach_in:
                if (
                    db_teach.get("teacher_id") == db_teacher.get("_id") and
                    db_teach.get("course_id") == db_course.get("_id")
                ):
                    found = True
                    break
            
            if (found == True):
                continue

            new_teach_in.append({
                "teacher_id": db_teacher.get("_id"),
                "course_id": db_course.get("_id"),
                "available": True
            })

    if (len(new_teach_in) == 0):
        return
    
    try:
        db.teach_in.insert_many(new_teach_in)
    except Exception as e:
        print(e)

    return

### LIST COURSE SCHEDULES ###
def list_course_schedules(db, course):
    '''
        Get all the room schedules for a course in a semester
        Input:
            - course: the course object
        Output:
            - schedules: a list of schedules
    '''

    # Get course db object
    db_course = db.courses.find_one({"code": course.get("code")})
    if (db_course is None):
        print("Course not found in db")
        return []

    # Get semester
    semester_type = course.get("semester")
    if (semester_type is None):
        return []
    
    if (semester_type == "Automne"):
        semester_type = "fall"
    elif (semester_type == "Printemps"):
        semester_type = "spring"    

    # Get course schedule
    course_schedule = course.get("schedule")

    if (course_schedule is None):
        return []
    
    if (semester_type == "ecole_doctorale"):
        schedules = []

        # Loop through the course schedule for that day
        for schedule in course_schedule:

            date = schedule.get('date')
            start_hour = schedule.get('start_hour')
            duration = schedule.get('duration', 1)  # default to 1 hour if not specified

            schedule = {
                'course_id': db_course.get('_id'),
                'start_datetime': datetime.combine(date, datetime.min.time()).replace(hour=start_hour),
                'end_datetime': datetime.combine(date, datetime.min.time()).replace(hour=start_hour + duration),
                'label': schedule.get('label'),
                'available': True,
                'rooms': schedule.get('rooms')
            }
            schedules.append(schedule)
        return schedules
    else:
        # Map from number to day of the week
        map_days = {
            0: 'Lu',
            1: 'Ma',
            2: 'Me',
            3: 'Je',
            4: 'Ve'
        }
        
        semester = db.semesters.find_one({"type": semester_type})
        if (semester is None):
            print("Semester not found in db")
            return []

        semester_start = semester.get("start_date")
        semester_end = semester.get("end_date")

        schedules = []
        
        # Loop through every date in the semester
        current_date = semester_start
        while current_date <= semester_end:
            weekday = current_date.weekday()

            # If it's not a weekday (Saturday or Sunday), skip
            if weekday not in map_days:
                current_date += timedelta(days=1)
                continue

            day_abbr = map_days[current_date.weekday()]
            
            # Loop through the course schedule for that day
            for time, time_schedule in course_schedule.items():
                if day_abbr in time_schedule:
                    entry = time_schedule[day_abbr]
                    
                    # If it's not a 'skip' entry, create a booking
                    if not entry.get('skip') or entry.get('skip') == False:
                        start_hour = int(time.split('-')[0])
                        duration = entry.get('duration', 1)  # default to 1 hour if not specified
                        schedule = {
                            'course_id': db_course.get('_id'),
                            'start_datetime': datetime.combine(current_date, datetime.min.time()).replace(hour=start_hour),
                            'end_datetime': datetime.combine(current_date, datetime.min.time()).replace(hour=start_hour + duration),
                            'label': entry['label'],
                            'available': True,
                            'rooms': entry['rooms']
                        }
                        schedules.append(schedule)
            
            current_date += timedelta(days=1)

    return schedules

### CREATE COURSE SCHEDULES ###
def create_course_schedules(db, course):
    '''
        Create all the schedules for a course in a semester
        Input:
            - course: the course to create the bookings for
        Output:
            - None
    '''

    db_course = db.courses.find_one({"code": course.get("code")})
    if (db_course is None):
        print("Course not found in db")
        return None

    schedules = list_course_schedules(db, course)

    if schedules is None:
        return
    
    if (len(schedules) == 0):
        return
    

    db_schedules = list(db.course_schedules.find({
        "course_id": schedules[0].get("course_id"),
    }))

    new_schedules = []
    for schedule in schedules:
        found = False
        for db_schedule in db_schedules:
            if (
                schedule.get('course_id') == db_schedule.get('course_id') and
                schedule.get('start_datetime') == db_schedule.get('start_datetime') and
                schedule.get('end_datetime') == db_schedule.get('end_datetime')):
                found = True
                break
        if not found:
            new_schedule = {
                "course_id": schedule.get("course_id"),
                "start_datetime": schedule.get("start_datetime"),
                "end_datetime": schedule.get("end_datetime"),
                "label": schedule.get("label"),
                "available": True
            }
            new_schedules.append(new_schedule)

    if (len(new_schedules) == 0):
        return
    
    try:
        db.course_schedules.insert_many(new_schedules)
    except Exception as e:
        print(e)

    return

### CREATE COURSE BOOKINGS ###
def create_course_bookings(db, course):
    '''
        Create all the bookings for a course in a semester
        Input:
            - course: the course to create the bookings for
        Output:
            - None
    '''

    db_course = db.courses.find_one({"code": course.get("code")})
    if (db_course is None):
        print("Course not found in db")
        return None

    # Get all schedules of a course and add a rooms field as a list of room names of the bookings linked to the schedule
    db_schedules = list(db.course_schedules.aggregate([
        {
            "$match": {
                "course_id": db_course.get("_id")
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
            "$lookup": {
                "from": "rooms",
                "localField": "bookings.room_id",
                "foreignField": "_id",
                "as": "rooms"
            }
        },
        {
            "$addFields": {
                "rooms": "$rooms"
            }
        }
    ]))

    schedules = list_course_schedules(db, course)

    if (len(schedules) == 0):
        return

    new_bookings = []
    for schedule in schedules:
        db_schedule_found = None
        for db_schedule in db_schedules:
            if (
                schedule.get('course_id') == db_schedule.get('course_id') and
                schedule.get('start_datetime') == db_schedule.get('start_datetime') and
                schedule.get('end_datetime') == db_schedule.get('end_datetime')):
                db_schedule_found = db_schedule
                break
        
        if db_schedule_found is None:
            print("Schedule not found in db")
            continue

        unique_rooms = list(set(schedule.get('rooms')))

        for room_name in unique_rooms:
            found = False
            for db_room in db_schedule_found.get('rooms'):
                if (
                    room_name == db_room.get('name')):
                    found = True
                    break

            if found == False:
                room = db.rooms.find_one({"name": room_name})
                if (room is None):
                    print("Room not found in db")
                    continue
                new_booking = {
                    "schedule_id": db_schedule_found.get("_id"),
                    "room_id": room.get("_id"),
                    "available": True
                }
                new_bookings.append(new_booking)

    if (len(new_bookings) == 0):
        return
    
    try:
        db.course_bookings.insert_many(new_bookings)
    except Exception as e:
        print(e)

    return

def create_courses_schedules_and_bookings(db, courses):
    '''
        Create all the schedules and bookings for a list of courses in a semester
        Input:
            - courses: the list of courses to create the bookings for
        Output:
            - None
    '''

    for course in tqdm(courses):
        create_course_schedules(db, course)
        create_course_bookings(db, course)

    return


### GET COURSE ROOMS ###
def get_course_rooms(db, course):
    '''
        Get all the rooms objects for a course
        Input:
            - course: the course object
        Output:
            - rooms: a list of rooms
    '''

    rooms_names = []

    course_schedule = course.get("schedule")

    if (course_schedule is None):
        return []

     # Loop through the course schedule
    for _, time_schedule in course_schedule.items():
        for _, entry in time_schedule.items():
            
            # If it's not a 'skip' entry, create a booking
            if not entry.get('skip') or entry.get('skip') == False:
                for room in entry['rooms']:
                    if room not in rooms_names:
                        rooms_names.append(room)

    if (len(rooms_names) == 0):
        return []
    
    rooms = list(db.rooms.find({"name": {"$in": rooms_names}}))

    return rooms


### LIST ALL ROOMS ###
def list_rooms(courses):

    rooms = []
    for course in courses:
        course_rooms = list_course_rooms(course)
        for room in course_rooms:
            if room not in rooms:
                rooms.append(room)

    return rooms

### LIST COURSE ROOMS ###
def list_course_rooms(course):
    rooms_names = []

    course_schedule = course.get("schedule")

    if (course_schedule is None):
        return []
    
    if (course.get('semester') == 'ecole_doctorale'):
        for schedule in course_schedule:
            for room in schedule['rooms']:
                if room not in rooms_names:
                    rooms_names.append(room)

    else:
        # Loop through the course schedule
        for _, time_schedule in course_schedule.items():
            for _, entry in time_schedule.items():
                
                # If it's not a 'skip' entry, create a booking
                if not entry.get('skip') or entry.get('skip') == False:
                    for room in entry['rooms']:
                        if room not in rooms_names:
                            rooms_names.append(room)


    return rooms_names


### CREATE ROOMS ###
def create_rooms(db, courses):
    '''
        Create rooms in the database
        Input:
            - db: the database
            - room_names: a list of room names
    '''

    # List all rooms in the courses schedules
    rooms_names = list_rooms(courses)

    # Find all rooms on plan.epfl.ch
    print("Getting rooms from plan.epfl.ch")
    plan_rooms = list_plan_rooms()
    plan_rooms_names = [plan_room.get("name") for plan_room in plan_rooms]


    # List all rooms in the database
    print("Getting rooms from database")
    db_rooms = list(db.rooms.find({}))

    # Update the type of the rooms in the database if necessary
    print("Updating rooms in database")
    for db_room in tqdm(db_rooms):
        db_room_name = db_room.get("name")
        db_room_type = db_room.get("type")
        if (db_room_name not in plan_rooms_names):
            # If the room is not on plan.epfl.ch, ignore it
            continue
        plan_room = [plan_room for plan_room in plan_rooms if plan_room.get("name") == db_room_name][0]
        plan_room_type = plan_room.get("type")
        if (db_room_type != plan_room_type):
            db.rooms.update_one({"name": db_room_name}, { "$set": { "type": plan_room_type }})

    # List rooms to create
    db_rooms_names = [db_room.get("name") for db_room in db_rooms]
    new_rooms_names = [room_name for room_name in rooms_names if room_name not in db_rooms_names]

    # Create the rooms that are not in the database
    print("Creating new rooms in database")
    new_rooms = []
    for room_name in tqdm(new_rooms_names):
        plan_room = [plan_room for plan_room in plan_rooms if plan_room.get("name") == room_name] 
        if (plan_room is None):
            room_type = "unknown"
        elif (len(plan_room) == 0):
            room_type = "unknown"
        else:
            room_type = plan_room[0].get("type", "unknown")
        
        new_rooms.append({"name": room_name, "type": room_type, "available": True})

    try:
        db.rooms.insert_many(new_rooms)
    except Exception as e:
        print(e)

    return
            




### LIST ALL PLAN ROOMS ###
def list_plan_rooms():
    '''
        List all the rooms objects (name, type) on the plan.epfl.ch website
        Output:
            - rooms: a list of rooms
    '''

    def list_level_rooms(low, up, floor, max=1000):
        '''
            List all the XML rooms objects in a level
            Input:
                - low: the lower left corner of the level
                - up: the upper right corner of the level
                - floor: the floor of the level
                - max: the maximum number of rooms to return
                Output:
                    - rooms: a list of XML rooms
        '''
        low1, low2 = low
        up1, up2 = up
        request_url = f"https://plan.epfl.ch/mapserv_proxy?ogcserver=source+for+image%2Fpng&cache_version=9fe661ce469e4692b9e402b22d8cb420&floor={floor}"
        xml = f'<GetFeature xmlns="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="GML3" maxFeatures="{max}" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd"><Query typeName="feature:batiments_wmsquery" srsName="EPSG:2056" xmlns:feature="http://mapserver.gis.umn.edu/mapserver"><Filter xmlns="http://www.opengis.net/ogc"><BBOX><PropertyName>the_geom</PropertyName><Envelope xmlns="http://www.opengis.net/gml" srsName="EPSG:2056"><lowerCorner>{low1} {low2}</lowerCorner><upperCorner>{up1} {up2}</upperCorner></Envelope></BBOX></Filter></Query></GetFeature>'

        r = requests.post(request_url, data=xml)
        level_xml = BeautifulSoup(r.text, 'xml')
        if (level_xml.find('gml:Null') != None):
            return None
        return level_xml.findAll('gml:featureMember')
    
    def list_all_levels_rooms():
        '''
            List all the XML rooms objects in ALL levels
            Output:
                - rooms: a list of XML rooms
        '''
        rooms_xml = []
        for level in tqdm(range(-3, 6)):
            level_rooms_xml = list_level_rooms((2533565.4081416847, 1152107.9784703811), (2532650.4135850836, 1152685.3502971812), level, max=5000)
            if (level_rooms_xml and len(level_rooms_xml) > 0):
                rooms_xml += level_rooms_xml
        return rooms_xml

    def parse_room(room_xml):
        '''
            Parse a XML room object
            Input:
                - room_xml: the XML room object
            Output:
                - room: the parsed room object (name, type)
        '''
        room_name = BeautifulSoup(room_xml.find('ms:room_abr_link').text, 'html.parser').find('div', class_="room").text.replace(" ", "")
        room_type = room_xml.find('ms:room_uti_a').text
        return { 'name': room_name, 'type': room_type }
    
    def parse_all_rooms(rooms_xml):
        '''
            Parse all XML rooms objects
            Input:
                - rooms_xml: the XML rooms objects
            Output:
                - rooms: a list of parsed rooms objects (name, type)
        '''
        rooms_parsed = []
        for room_xml in rooms_xml:
            room = parse_room(room_xml)
            if (room == None):
                continue
            if (room not in rooms_parsed):
                rooms_parsed.append(room)
        return rooms_parsed
    
    rooms_xml = list_all_levels_rooms()
    rooms = parse_all_rooms(rooms_xml)

    return rooms

    
    
def list_courses_plan_studyplans():
    URL_BA = "https://edu.epfl.ch/studyplan/fr/bachelor/"
    URL_PROPE = "https://edu.epfl.ch/studyplan/fr/propedeutique/"
    URL_MASTER = "https://edu.epfl.ch/studyplan/fr/master/"
    URL_ROOT = 'https://edu.epfl.ch/'

    # Find all BA study plans for each section and all courses in them
    plans_etudes = []
    for url in [URL_MASTER, URL_BA, URL_PROPE]:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        sections = [x.get('href') for x in soup.find('main').find('ul').findAll('a')]
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
                        if (section_name not in MAP_SECTIONS):
                            continue
                        if (semester not in MAP_PROMOS):
                            continue

                        plans_etudes.append({
                            "code": code,
                            "promo": MAP_PROMOS[semester],
                            "section": section_name
                        })

    return plans_etudes

def list_units(planned_in):
    units = []
    for plan in planned_in:
        if (plan['promo'], plan['section']) not in units:
            units.append((plan['promo'], plan['section']))

    return units

def create_units(db, planned_in):

    units = list_units(planned_in)

    db_units = list(db.units.find())
    db_units_names = [unit.get('name') for unit in db_units]

    map_promo_to_name = {v: k for k, v in MAP_PROMOS.items()}

    new_units = []
    for unit in tqdm(units):
        unit_name = unit[1] + ' - ' + map_promo_to_name[unit[0]]
        if (unit_name not in db_units_names):
            new_units.append({
                'code': MAP_SECTIONS[unit[1]] + '-' + unit[0],
                'promo': unit[0],
                'section': MAP_SECTIONS[unit[1]],
                'name': unit_name,
                'available': True
            })

    if (len(new_units) == 0):
        return
    
    try:
        db.units.insert_many(new_units)
    except Exception as e:
        print(e)

    return

def create_studyplans(db, planned_in):
    db_studyplans = list(db.studyplans.find({
        'available': True
    }))
    db_semesters = list(db.semesters.find({
        'available': True
    }))

    db_units = list(db.units.find({ 'available': True }))

    map_promo_to_name = {v: k for k, v in MAP_PROMOS.items()}

    unique_planned_in = []
    unique_planned_in_ids = []
    for plan in tqdm(planned_in):
        if (plan['promo'], plan['section']) not in unique_planned_in_ids:
            unique_planned_in.append(plan)
            unique_planned_in_ids.append((plan['promo'], plan['section']))

    new_studyplans = []
    for plan in unique_planned_in:
        plan_name = plan['section'] + ' - ' + map_promo_to_name[plan['promo']]
        plan_unit = list(filter(lambda unit: unit['name'] == plan_name, db_units))[0]
        if (plan_unit == None):
            print('Unit not found')
            continue
        plan_semester = list(filter(lambda semester: MAP_SEMESTERS[plan.get('promo')] == semester.get('type'), db_semesters))[0]
        if (plan_semester == None):
            print('Semester not found')
            continue

        found = False

        for db_plan in db_studyplans:
            if (
                db_plan['unit_id'] == plan_unit['_id'] and
                db_plan['semester_id'] == plan_semester['_id']
            ):
                found = True
                break
        if (found == True):
            continue

        new_studyplans.append({
            'unit_id': plan_unit['_id'],
            'semester_id': plan_semester['_id'],
            'available': True,
        })

    if (len(new_studyplans) == 0):
        return
    
    try:
        db.studyplans.insert_many(new_studyplans)
    except Exception as e:
        print(e)

    return

def create_planned_in(db, planned_in):
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

    db_studyplans = list(db.studyplans.aggregate(pipeline))

    db_planned_in = list(db.planned_in.find({
        'available': True
    }))

    map_promo_to_name = {v: k for k, v in MAP_PROMOS.items()}

    new_planned_in = []
    for plan in tqdm(planned_in):
        plan_unit_name = plan['section'] + ' - ' + map_promo_to_name[plan['promo']]
        plan_semester = MAP_SEMESTERS[plan.get('promo')]

        db_course = db.courses.find_one({
            'code': plan.get('code')
        })
        if (db_course == None):
            continue

        studyplan = list(filter(lambda studyplan: studyplan['unit'][0].get('name') == plan_unit_name and studyplan['semester'][0].get('type') == plan_semester, db_studyplans))

        if (len(studyplan) == 0):
            print('Studyplan not found')
            continue

        studyplan = studyplan[0]

        if (studyplan == None):
            print('Studyplan not found')
            continue

        found = False
        for db_plan in db_planned_in:
            if (
                db_plan['course_id'] == db_course['_id'] and
                db_plan['studyplan_id'] == studyplan['_id']
            ):
                found = True
                break

        if (found == True):
            continue

        new_planned_in.append({
            'course_id': db_course['_id'],
            'studyplan_id': studyplan['_id'],
            'available': True,
        })

    if (len(new_planned_in) == 0):
        return
    
    try:
        db.planned_in.insert_many(new_planned_in)
    except Exception as e:
        print(e)

    return
