// services/rooms.ts
import { ObjectId } from 'mongoose';
import { CourseBookingModel, CourseScheduleModel, EventBookingModel, RoomModel } from '../db/models';

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
    }).select(['name', 'type', 'coordinates', 'building']).lean();
    return rooms;
}

export const fetchRoom = async (room_name: string) => {
    /*
        Fetch room by name
        - Inputs:
            - room_name: string
        - Outputs:
            - Room (_id, name, type, coordinates, building)
    */

    const room = await RoomModel.findOne({
        name: room_name
    }).lean();
    return room;
}

export const fetchBookedRoomsIds = async (query_conditions: any) => {

    const constraining_course_schedules = await CourseScheduleModel.find({
        "$or": query_conditions,
        available: true
    }).lean().exec();

    const course_booked_rooms = await CourseBookingModel.find({
        schedule_id: {
            $in: constraining_course_schedules.map(({ _id }: any) => _id)
        },
        available: true
    }).lean().exec();
    const course_booked_rooms_ids = course_booked_rooms.map(({ room_id }: any) => room_id);

    const event_booked_rooms = await EventBookingModel.find({
        "$or": query_conditions,
        available: true
    }).lean().exec();

    const event_booked_rooms_ids = event_booked_rooms.map(({ room_id }: any) => room_id);

    const booked_rooms_ids = [...course_booked_rooms_ids, ...event_booked_rooms_ids];

    return booked_rooms_ids;
}

export const sortRoomsByDistance = async (rooms: any, coordinates: any, ascending = true) => {
    /*
        Sort rooms by distance
        - Inputs:
            - rooms: Array of rooms (name, type)
            - coordinates: Object with latitude and longitude properties
        - Outputs:
            - Array of rooms (name, type, distance)
    */

    const rooms_with_distance = await Promise.all(rooms.map(async (room: any) => {
        const room_coordinates = { latitude: room.coordinates[0], longitude: room.coordinates[1] };

        // Calculate distance between room and coordinates
        const distance = await computeDistance(room_coordinates, coordinates);

        return { ...room, distance };
    }));

    const sorted_rooms = rooms_with_distance.sort((a: any, b: any) => {
        if (ascending) return a.distance - b.distance;
        return b.distance - a.distance;
    });

    return sorted_rooms;
}

const computeDistance = async (coords_a: any, coords_b: any) => {
    /*
        Compute distance between two coordinates
        - Inputs:
            - coords_a: Object with latitude and longitude properties
            - coords_b: Object with latitude and longitude properties
        - Outputs:
            - Distance in meters
    */

    const R = 6371e3; // meters
    const phi1 = coords_a.latitude * Math.PI / 180; // phi, lambda in radians
    const phi2 = coords_b.latitude * Math.PI / 180;
    const delta_phi = (coords_b.latitude - coords_a.latitude) * Math.PI / 180;
    const delta_lambda = (coords_b.longitude - coords_a.longitude) * Math.PI / 180;

    const a = Math.sin(delta_phi / 2) * Math.sin(delta_phi / 2) +
        Math.cos(phi1) * Math.cos(phi2) *
        Math.sin(delta_lambda / 2) * Math.sin(delta_lambda / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    const d = R * c; // in meters

    return d;
}


export const fetchSoonestBooking = async (after_date: Date, room_id: ObjectId) => {
    const course_bookings = (await CourseBookingModel.find({
        available: true,
        room_id
    }).populate('schedule')
        .sort({ 'schedule.end_datetime': 1 })
        .lean())
        .map(({ schedule }: any) => {
            const { start_datetime, end_datetime } = schedule;
            return { start_datetime, end_datetime };
        });

    const event_bookings = await EventBookingModel.find({
        available: true,
        room_id
    }).sort({ 'end_datetime': 1 })
        .lean();

    const soonest_booking = [...course_bookings, ...event_bookings].reduce((acc: any, booking: any) => {
        const { start_datetime, end_datetime } = booking;

        if (end_datetime > after_date) {
            if (!acc.end_datetime) {
                acc = { start_datetime, end_datetime };
            } else if (acc.end_datetime > end_datetime) {
                acc = { start_datetime, end_datetime };
            }
        }

        return acc;
    }, {});

    return soonest_booking;
}

export const fetchSoonestBookingsPerRoom = async (after_date: Date) => {
    const course_bookings = (await CourseBookingModel.find({
        available: true,
    }).populate('schedule')
        .sort({ 'schedule.end_datetime': 1 })
        .lean())
        .map(({ schedule, room_id }: any) => {
            const { start_datetime, end_datetime } = schedule;
            return { room_id, start_datetime, end_datetime };
        });

    const event_bookings = await EventBookingModel.find({
        available: true,
    }).sort({ 'end_datetime': 1 })
        .lean();


    // sort bookings by room
    const sorted_bookings = [...course_bookings, ...event_bookings].reduce((acc: any, booking: any) => {
        const { room_id, start_datetime, end_datetime } = booking;

        if (end_datetime < after_date) return acc;

        if (!acc[room_id]) {
            acc[room_id] = [];
        }

        acc[room_id].push({ start_datetime, end_datetime });

        return acc;
    }, {});

    let soonest_booking_per_room = {} as any;
    for (const room_id in sorted_bookings) {
        let room_sorted_bookings = sorted_bookings[room_id].sort((a: any, b: any) => {
            return a.start_datetime - b.start_datetime;
        });
        
        let soonest_booking = room_sorted_bookings.reduce((acc: any, booking: any) => {
            let soonestSchedule = null;
            for (let i = 0; i < room_sorted_bookings.length; i++) {
                let current = room_sorted_bookings[i];

                if (new Date(current.end_datetime) < new Date()) continue;

                // if no soonestSchedule, set the current schedule as current
                if (!soonestSchedule) {
                    soonestSchedule = current;
                    continue;
                }

                // Check if the current schedule ends when the next one starts
                if (soonestSchedule && new Date(soonestSchedule.end_datetime).getTime() === new Date(current.start_datetime).getTime()) {
                    soonestSchedule = {
                        start_datetime: soonestSchedule.start_datetime,
                        end_datetime: current.end_datetime
                    };
                    continue;
                }

                return soonestSchedule;

            }
            return soonestSchedule;
        }, room_sorted_bookings[0]);

        soonest_booking_per_room[room_id] = soonest_booking;
            
    }

    return soonest_booking_per_room;
}