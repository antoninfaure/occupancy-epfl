import { Schema, model, Types } from "mongoose";

/// ROOM
const RoomSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    type: {
        type: String,
        required: true
    },
    link: String,
    coordinates: {
        latitude: Number,
        longitude: Number
    },
    capacity: Number
}, { collection: 'rooms' });

/// TEACHER
const TeacherSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    people_url: {
        type: String,
        required: true
    }
}, { collection: 'teachers' });


/// COURSE
const CourseSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    code: {
        type: String,
        required: true
    },
    credits: {
        type: Number,
        required: true
    },
    edu_url: String,
    language: String,
    teachers: [
        {
            type: Types.ObjectId,
            ref: 'Teacher'
        }
    ]
}, { collection: 'courses' });

CourseSchema.virtual('planned_ins', {
    ref: 'PlannedIn',
    localField: '_id',
    foreignField: 'course_id'
})


/// COURSE SCHEDULE
const CourseScheduleSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    course_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Course'
    },
    start_datetime: {
        type: String,
        required: true
    },
    end_datetime: {
        type: String,
        required: true
    },
    label: {
        type: String,
        required: true
    }
}, { collection: 'course_schedules' });

CourseScheduleSchema.virtual('course', {
    ref: 'Course',
    localField: 'course_id', 
    foreignField: '_id',
    justOne: true
});

CourseScheduleSchema.virtual('bookings', {
    ref: 'CourseBooking',
    localField: '_id', 
    foreignField: 'schedule_id' 
});


/// EVENT SCHEDULE
const EventScheduleSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    start_datetime: {
        type: String,
        required: true
    },
    end_datetime: {
        type: String,
        required: true
    },
    label: {
        type: String,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    description: String
}, { collection: 'event_schedules' });


/// COURSE BOOKING
const CourseBookingSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    room_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Room'
    },
    schedule_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'CourseSchedule'
    }
}, { collection: 'course_bookings' });

CourseBookingSchema.virtual('room', {
    ref: 'Room',
    localField: 'room_id', 
    foreignField: '_id',
    justOne: true
});

CourseBookingSchema.virtual('schedule', {
    ref: 'CourseSchedule',
    localField: 'schedule_id', 
    foreignField: '_id' ,
    justOne: true
});



/// EVENT BOOKING
const EventBookingSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    room_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Room'
    },
    schedule_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'EventSchedule'
    }
}, { collection: 'event_bookings' });

EventBookingSchema.virtual('room', {
    ref: 'Room',
    localField: 'room_id', 
    foreignField: '_id',
    justOne: true 
});

EventBookingSchema.virtual('schedule', {
    ref: 'EventSchedule',
    localField: 'schedule_id', 
    foreignField: '_id',
    justOne: true
});


/// STUDYPLAN
const StudyplanSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    unit_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Unit',
    },
    semester_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Semester'
    }
}, { collection: 'studyplans' });

StudyplanSchema.virtual('unit', {
    ref: 'Unit',
    localField: 'unit_id', 
    foreignField: '_id' ,
    justOne: true
});

StudyplanSchema.virtual('semester', {
    ref: 'Semester',
    localField: 'semester_id', 
    foreignField: '_id',
    justOne: true
});


/// PLANNED IN
const PlannedInSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    course_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Course'
    
    },
    studyplan_id: {
        type: Types.ObjectId,
        required: true,
        ref: 'Studyplan'
    }
}, { collection: 'planned_in' });

PlannedInSchema.virtual('course', {
    ref: 'Course',
    localField: 'course_id', 
    foreignField: '_id',
    justOne: true
});

PlannedInSchema.virtual('studyplan', {
    ref: 'Studyplan',
    localField: 'studyplan_id', 
    foreignField: '_id',
    justOne: true 
});


/// SEMESTER
const SemesterSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    start_date: {
        type: String,
        required: true
    },
    end_date: {
        type: String,
        required: true
    },
    type: {
        type: String,
        required: true
    },
    skip_dates: [String]
}, { collection: 'semesters' });


/// UNIT
const UnitSchema = new Schema({
    available: {
        type: Boolean,
        required: true
    },
    name: {
        type: String,
        required: true
    },
    code: {
        type: String,
        required: true
    },
    section: String,
    promo: String
}, { collection: 'units' });


export const RoomModel = model('Room', RoomSchema);
export const TeacherModel = model('Teacher', TeacherSchema);
export const CourseModel = model('Course', CourseSchema);
export const CourseScheduleModel = model('CourseSchedule', CourseScheduleSchema);
export const EventScheduleModel = model('EventSchedule', EventScheduleSchema);
export const CourseBookingModel = model('CourseBooking', CourseBookingSchema);
export const EventBookingModel = model('EventBooking', EventBookingSchema);
export const StudyplanModel = model('Studyplan', StudyplanSchema);
export const PlannedInModel = model('PlannedIn', PlannedInSchema);
export const SemesterModel = model('Semester', SemesterSchema);
export const UnitModel = model('Unit', UnitSchema);