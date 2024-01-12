// services/bookings.ts
import { CourseBookingModel, CourseScheduleModel, EventBookingModel } from '../db/models';
import { Types } from 'mongoose';

export const fetchRoomCourseSchedules = async (room_id: Types.ObjectId) => {
    /*
        Fetch all courses_schedules for a room
        - Inputs:
            - room_id
        - Outputs:
            - Array of schedules (course, start_datetime, end_datetime, label)
    */

    const schedules = await CourseBookingModel.find({
        room_id: room_id,
        available: true
    })
    .select('-room_id')
    .populate({
        path: 'schedule',
        populate: {
            path: 'course',
            select: "code name"
        }
    })
    .lean()
    .exec()

    return schedules.map(({ schedule } : any) => {
        const { course, start_datetime, end_datetime, label } = schedule;
        const { code, name } = course;
        const dayBefore = new Date(start_datetime);
        dayBefore.setHours(dayBefore.getHours() - 1); // UTC+1
        dayBefore.setDate(dayBefore.getDate() - 1); // day before
        if (end_datetime < dayBefore) return null;
        return {
            course: {
                code,
                name
            },
            start_datetime,
            end_datetime,
            label
        };
    }).filter((schedule: any) => schedule !== null);
}

export const fetchRoomEventSchedules = async (room_id: Types.ObjectId) => {
    /*
        Fetch all event_schedules for a room
        - Inputs:
            - room_id
        - Outputs:
            - Array of schedules (event, start_datetime, end_datetime, label)
    */

    const bookings = await EventBookingModel.find({
        room_id: room_id,
        available: true
    }).populate({
        path: 'schedule_id'
    }).lean().exec();

    return bookings.map(({ schedule_id } : any) => {
        return {
            ...schedule_id
        };
    });
}

export const fetchCourseSchedules = async (course_id: Types.ObjectId) => {
    /*
        Fetch all courses_schedules for a course
        - Inputs:
            - course_id
        - Outputs:
            - Array of schedules (start_datetime, end_datetime, label, rooms)
    */


    const schedules = await CourseScheduleModel.find({
        course_id: course_id,
        available: true
    })
    .select('start_datetime end_datetime label')
    .populate({
        path: 'bookings',
        populate: {
            path: 'room',
            select: "code name -_id"
        },
        select: 'room room_id -_id -schedule_id'
    })
    .lean().exec();

    const results = schedules.map(({ bookings, start_datetime, end_datetime, label }: any) => {
        const rooms = bookings.map((booking: any) => booking.room)
        
        return {
            start_datetime,
            end_datetime,
            label,
            rooms
        }
    })

    return results
}

export const fetchCoursesSchedules = async (courses_ids: Types.ObjectId[]) => {
    /*
        Fetch all courses_schedules for list of courses
        - Inputs:
            - Array of courses_ids
        - Outputs:
            - Array of schedules (course, start_datetime, end_datetime, label, rooms)
    */


    const schedules = await CourseScheduleModel.find({
        course_id: { $in: courses_ids },
        available: true
    })
    .populate({
        path: 'bookings',
        populate: {
            path: 'room',
            select: "code name -_id"
        },
        select: 'room room_id -_id -schedule_id'
    })
    .populate('course')
    .lean().exec();

    const results = schedules.map(({ bookings, start_datetime, end_datetime, label, course }: any) => {
        const rooms = bookings.map((booking: any) => booking.room)
        if (course) course = {
            code: course.code,
            name: course.name
        }
        return {
            course,
            start_datetime,
            end_datetime,
            label,
            rooms
        }
    })

    return results
}