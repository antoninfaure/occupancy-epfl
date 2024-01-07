// services/rooms.ts
import { CourseBookingModel, CourseScheduleModel, EventBookingModel, EventScheduleModel, RoomModel } from '../db/models';

export const fetchRooms = async () => {
    /*
        Fetch all rooms
        - Inputs:
            - None
        - Outputs:
            - Array of rooms (name, type)
    */

    const rooms = await RoomModel.find({
        available: true
    }).select(['-_id', 'name', 'type']).lean();
    return rooms;
}

export const fetchRoom = async (room_name: string) => {
    /*
        Fetch room by name
        - Inputs:
            - room_name: string
        - Outputs:
            - Room (name, type)
    */

    const room = await RoomModel.findOne({
        name: room_name
    }).lean();
    return room;
}

export const fetchBookedRoomsIds = async (query_conditions: any) => {
    const constraining_course_schedules = await CourseScheduleModel.find({
        $or: query_conditions
    }).lean().exec();
    const course_booked_rooms = await CourseBookingModel.find({
        schedule_id: {
            $in: constraining_course_schedules.map(({ _id }: any) => _id)
        }
    }).lean().exec();
    const course_booked_rooms_ids = course_booked_rooms.map(({ room_id }: any) => room_id);

    const constraining_event_schedules = await EventScheduleModel.find({
        $or: query_conditions
    }).lean().exec();
    const event_booked_rooms = await EventBookingModel.find({
        schedule_id: {
            $in: constraining_event_schedules.map(({ _id }: any) => _id)
        }
    }).lean().exec();
    const event_booked_rooms_ids = event_booked_rooms.map(({ room_id }: any) => room_id);

    const booked_rooms_ids = [...course_booked_rooms_ids, ...event_booked_rooms_ids];

    return booked_rooms_ids;
}