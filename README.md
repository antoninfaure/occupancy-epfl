# :clock1: [Occupancy FLEP - Backend](https://occupancy.flep.ch/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Interface of edu.epfl.ch, useful for finding free rooms or schedule by studyplan.

## Features

- **Room Availability**: Find available rooms based on selected date and time ranges. The system displays rooms that are not booked during the specified time slots.
  
- **Retrieve Course Information**: Easily find detailed information about a specific course by providing its code. The system retrieves details such as the course's semester, assigned teachers, and schedules.

- **Explore Study Plans**: Explore study plans using their unique study plan ID. The application showcases an interactive and organized timetable that covers the entire semester, highlighting courses, schedules, and room bookings.



## Frontend
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB) ![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white) ![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2306B6D4.svg?style=for-the-badge&logo=tailwindcss&logoColor=white&color=%2306B6D4) ![GitHub](https://img.shields.io/badge/GitHub-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)

The frontend repository can be found **[here](https://github.com/antoninfaure/occupancy-front)**

## Scraper
 ![Python](https://img.shields.io/badge/Python-%23000.svg?style=for-the-badge&logo=Python&logoColor=white&color=%233776AB) ![MongoDB](https://img.shields.io/badge/MongoDB-%23000.svg?style=for-the-badge&logo=MongoDB&logoColor=white&color=%2347A248) ![GitHub](https://img.shields.io/badge/GitHub-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)

The scraper repository can be found **[here](https://github.com/antoninfaure/occupancy-scraper)**

## Backend
![Node.js](https://img.shields.io/badge/Node.js-%23000.svg?style=for-the-badge&logo=Node.js&logoColor=white&color=%23339933) ![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white) ![MongoDB](https://img.shields.io/badge/MongoDB-%23000.svg?style=for-the-badge&logo=MongoDB&logoColor=white&color=%2347A248) ![Heroku](https://img.shields.io/badge/heroku-%23430098.svg?style=for-the-badge&logo=heroku&logoColor=white) 

The current repository is for the backend, which is a Node.js webapp used as a REST API for a MongoDB database, and hosted on Heroku.

### Run

In order to run this project, you must have **[Node.js](https://nodejs.org/)** installed.

1. Install the required dependencies:
```
npm install
```
2. Configure the environnement variables in the `.env` file

3. Launch the Node application:
```
npm run start
```

You can now go to [localhost:5000](http://localhost:5000) to see the page.

## Documentation

The API documentation can be found **[here](https://antoninfaure.github.io/occupancy-epfl/)**

## ER Model

```mermaid
erDiagram
    EVENT_BOOKING }o--|| EVENT_SCHEDULE : "is for (if meeting-related)"
    COURSE_BOOKING }o--|| ROOM : "occupies"
    COURSE_BOOKING }o--|| COURSE_SCHEDULE : "is for (if course-related)"
    COURSE ||--o{ COURSE_SCHEDULE : "has"
    EVENT_BOOKING }o--|| ROOM : "occupies"
    TEACHER }o--o{ COURSE: "teach in"
    COURSE ||--o{ PLANNED_IN : "is included in"
    STUDYPLAN ||--o{ PLANNED_IN : "consists of"
    STUDYPLAN }o--|| SEMESTER : "runs during"
    UNIT ||--o{ STUDYPLAN : "is composed of"

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

    UNIT {
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
- [Androz2091](https://github.com/Androz2091) for the geolocalisation feature
- [buercher](https://github.com/buercher) for creating a [Telegram Bot](https://github.com/buercher/NotEnoughRoomBot)
