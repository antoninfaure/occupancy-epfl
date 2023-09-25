# :clock1: [Occupancy FLEP - Backend](https://occupancy.flep.ch/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Interface of edu.epfl.ch, useful for finding free rooms or schedule by studyplan.

## Features

- **Room Availability**: Find available rooms based on selected date and time ranges. The system displays rooms that are not booked during the specified time slots.
  
- **Retrieve Course Information**: Easily find detailed information about a specific course by providing its code. The system retrieves details such as the course's semester, assigned teachers, and schedules.

- **Explore Study Plans**: Explore study plans using their unique study plan ID. The application showcases an interactive and organized timetable that covers the entire semester, highlighting courses, schedules, and room bookings.

## Frontend
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB) ![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white) ![SASS](https://img.shields.io/badge/SASS-hotpink.svg?style=for-the-badge&logo=SASS&logoColor=white) ![GitHub](https://img.shields.io/badge/GitHub-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)

The frontend repository can be found **[here](https://github.com/antoninfaure/occupancy-front)**

## Backend
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white) ![Heroku](https://img.shields.io/badge/heroku-%23430098.svg?style=for-the-badge&logo=heroku&logoColor=white)

The current repository is for the backend, which is a Flask webapp used as a REST API, and hosted on Heroku.

### Run

In order to run this project, you must have **[Flask](https://flask.palletsprojects.com/en/2.3.x/)** installed.

1. Install the required dependencies:
```
pip install -r requirements.txt
```
2. Configure the environnement variables in the `.env` file

3. Launch the Flask application:
```
flask run
```

You can now go to [localhost:5000](http://localhost:5000) to see the page.

### Data Scraping

To scrap the data you just need to configure the semesters (names, dates, types) in the `scrap.py` file and then run:
```
python scrap.py
```



## ER Model

```mermaid
erDiagram
    EVENT_BOOKING }o--|| EVENT_SCHEDULE : "is for (if meeting-related)"
    COURSE_BOOKING }o--|| ROOM : "occupies"
    COURSE_BOOKING }o--|| COURSE_SCHEDULE : "is for (if course-related)"
    COURSE ||--o{ COURSE_SCHEDULE : "has"
    TEACH_IN }o--|| COURSE : "relates to"
    EVENT_BOOKING }o--|| ROOM : "occupies"
    TEACHER ||--o{ TEACH_IN: "instructs"
    COURSE ||--o{ PLANNED_IN : "is included in"
    STUDYPLAN ||--o{ PLANNED_IN : "consists of"
    STUDYPLAN }o--|| SEMESTER : "runs during"
    ETU_UNIT ||--o{ STUDYPLAN : "is composed of"
    EVENT_SCHEDULE }o--|| ROLE : "booked"
    ROLE }o--|{ USER : "has role"
    ROLE }o--|{ UNIT : "in unit"
    ROOM }|--o{ MANAGED_BY : "managed by"
    MANAGED_BY }o--|{ ROLE : "manages"

    UNIT {
      string name
      bool available
    }

    ROLE {
        int user_id
        int unit_id
        int accred
        string name
        bool available
    }

    MANAGED_BY {
      int role_id
      int room_id
      int accred
      bool available
    }



    COURSE_BOOKING {
        int schedule_id FK
        int room_id FK
        bool available
    }



    EVENT_SCHEDULE {
        int role_id FK
        string name
        date start_datetime
        date end_datetime
        string type
        string description
        bool available
        bool visible
        int status
    }

   

    USER {
        int sciper
        string name
        string firstname
        bool available
    }

    ROOM {
        string name
        string capacity
        string type
        bool available
    }

    COURSE_SCHEDULE {
        int course_id FK
        date start_datetime
        date end_datetime
        string type
        bool available
    }
    
    COURSE {
        string code
        string name
        int credits
        string edu_url
        bool available
    }


    SEMESTER {
        string name
        string type
        date start_date
        date end_date
        bool available
    }

    ETU_UNIT {
        string name
        string code
        string promo
        string section
        bool available
    }

    TEACHER {
        string name
        string people_url
        bool available
    }

    EVENT_BOOKING {
        int schedule_id FK
        int room_id FK
        bool available
    }

```

## Contributing

Pull requests are welcome :smile:
