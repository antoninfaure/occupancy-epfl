
This document provides some documentation about the API endpoints of Occupancy FLEP API.

- [Endpoints](#endpoints)
  - [Courses](#courses)
  - [Study Plans](#study-plans)
  - [Rooms](#rooms)
- [Error Handling](#error-handling)

## Endpoints
### Courses

**GET** ```/api/courses```
Returns a list of all courses in the database.

- **Parameters**: None
- **Returns**: A list of all courses in the database.
  

**GET** ```/api/courses/<code>```

Returns detailed information about a specific course as well as its schedules and room bookings.

- **Parameters**: 
  - ```code```: The course code (e.g., ```CS-305```).
  
- **Returns**: A JSON object containing detailed information about the course, its schedules, and its room bookings.

### Study Plans

**GET** ```/api/studyplans```

Returns a list of all study plans in the database.

- **Parameters**: None
- **Returns**: A list of all study plans in the database.

**GET** ```/api/studyplans/<id>```

Returns detailed information about a specific study plan.

- **Parameters**: 
  - ```id```: The study plan ID
- **Returns**: A JSON object containing detailed information about the study plan, its courses and schedules.

### Rooms

**GET** ```/api/rooms```

Returns a list of all rooms in the database.

- **Parameters**: None
- **Returns**: A list of all rooms in the database.

**GET** ```/api/rooms/<name>```

Returns detailed information about a specific room as well as its bookings.

- **Parameters**: 
  - ```name```: The room name (e.g., ```CO1```).

- **Returns**: A JSON object containing detailed information about the room and its bookings.

**POST** ```/api/rooms/find_free_rooms```

Returns a list of available rooms based on the specified date and time ranges.

- **Parameters**: 
  - ```selection```: An array of objects containing the start and end datetimes of the desired time slots. The format is as follows:
    - ```start```: The start datetime of the time slot (e.g., ```2021-10-01T08:00```)
    - ```end```: The end datetime of the time slot (e.g., ```2021-10-01T10:00```)
- **Returns**: A list of available rooms based on the specified date and time ranges.

**POST** ```/api/rooms/find_soonest_bookings```

Return a list of rooms with the soonest (or current) booking for each room, after the specified datetime.

- **Parameters**: 
  - ```after_date```: The datetime after which the bookings should be returned (e.g., ```2021-10-01T08:00```)
- **Returns**: A list of rooms with the soonest booking for each room, after the specified datetime.

## Error Handling

The API returns the following error codes:
- ```400```: Bad request
- ```404```: Not found
- ...

When an error occurs, the API returns a JSON object with the following format:
```
{
  "message": "Bad request"
}
```