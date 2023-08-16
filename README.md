# :clock1: [Occupancy FLEP](https://occupancy.flep.ch/)
Interface of edu.epfl.ch, useful for finding free rooms or schedule by studyplan.

## Run

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

## Data Scraping

To scrap the data you just need to configure the semesters (names, dates, types) in the `scrap.py` file and then run:
```
python scrap.py
```

## Features

- **Room Availability**: Find available rooms based on selected date and time ranges. The system displays rooms that are not booked during the specified time slots.
  
- **Retrieve Course Information**: Easily find detailed information about a specific course by providing its code. The system retrieves details such as the course's semester, assigned teachers, and schedules.

- **Explore Study Plans**: Explore study plans using their unique study plan ID. The application showcases an interactive and organized timetable that covers the entire semester, highlighting courses, schedules, and room bookings.

## ER Model

```mermaid
erDiagram
    BOOKING }o--|| ROOM : "occupies"
    BOOKING }o--|| MEETING : "is for (if meeting-related)"
    BOOKING }o--|| SCHEDULE : "is for (if course-related)"
    COURSE ||--o{ SCHEDULE : "has"
    TEACH_IN }o--|| COURSE : "relates to"
    TEACHER ||--o{ TEACH_IN: "instructs"
    COURSE ||--o{ PLANNED_IN : "is included in"
    STUDYPLAN ||--o{ PLANNED_IN : "consists of"
    STUDYPLAN }o--|| SEMESTER : "runs during"
    ETU_UNIT ||--o{ STUDYPLAN : "is composed of"
    MEETING }o--|| UNIT : "booked"



    UNIT {
      string name
      bool available
    }

    BOOKING {
        int schedule_id FK "Optional"
        int meeting_id FK "Optional"
        int room_id FK
        bool available
    }

    MEETING {
        int unit_id FK
        date start_datetime
        date end_datetime
        string type
        string description
        bool available
    }

    ROOM {
        string name
        string capacity
        string type
        bool available
    }

    SCHEDULE {
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

```

## Contributing

Pull requests are welcome :smile:
