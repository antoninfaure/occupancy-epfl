// controllers/rooms.ts
import { Response, Request } from 'express';

import { fetchRooms, fetchRoom, fetchBookedRoomsIds, sortRoomsByDistance, fetchSoonestBookingsPerRoom } from "../services/rooms";
import { fetchRoomCourseSchedules, fetchRoomEventSchedules } from "../services/bookings";

export const getRooms = async (req: Request, res: Response) => {
    const rooms = await fetchRooms();

    const results = rooms.map(({ name, type, link, coordinates }: any) => {
        return { name, type, link, coordinates };
    })
    return res.status(200).json(results);
}

export const getRoom = async (req: Request, res: Response) => {
    const room_name = req.params.room_name || undefined;
    if (!room_name) return res.status(400).json({ message: "Missing room name" });

    const room = await fetchRoom(room_name);
    if (!room) return res.status(404).json({ message: "Room not found" });

    const room_id = room._id;

    // Get the room's schedules
    const course_schedules = await fetchRoomCourseSchedules(room_id);
    const event_schedules = await fetchRoomEventSchedules(room_id);

    // Add the bookings to the room object
    const { name, type, link, coordinates } = room
    const result = {
        name,
        type,
        link,
        coordinates,
        schedules: course_schedules.concat(event_schedules)
    }

    return res.status(200).json(result);
}

export const getAvailableRooms = async (req: Request, res: Response) => {
    const { selection, coordinates } = req.body;

    if (!selection) return res.status(400).json({ message: "Missing selection" });

    // Selection must be an array of { start_datetime, end_datetime }
    if (!Array.isArray(selection)) return res.status(400).json({ message: "Selection must be an array" });

    try {
        await Promise.all(selection.map((item: any) => {
            if (!item.start || !item.end) return Promise.reject(new Error("Selection must be an array of objects with start and end properties"));
        }));
    }
    catch (err: any) {
        return res.status(400).json({ message: err.message });
    }

    if (coordinates) {
        // Coordinates must be an object with latitude and longitude properties
        if (typeof coordinates !== "object") return res.status(400).json({ message: "Coordinates must be an object" });
        if (!coordinates.latitude || !coordinates.longitude) return res.status(400).json({ message: "Coordinates must have latitude and longitude properties" });
    }

    // Get all rooms
    const all_rooms = await fetchRooms();

    if (selection.length === 0) {
        if (!coordinates) return res.status(200).json(all_rooms);

        const sorted_rooms = await sortRoomsByDistance(all_rooms, coordinates);
        return res.status(200).json(sorted_rooms);
    }

    const datetime_ranges = selection.map(({ start, end }: any) => {
        const start_datetime = new Date(start);
        const end_datetime = new Date(end);
        return { start_datetime, end_datetime };
    });

    const query_conditions = datetime_ranges.map(({ start_datetime, end_datetime }: any) => {
        return {
            $or: [
                {"start_datetime": {"$lt": end_datetime}, "end_datetime": {"$gt": start_datetime}},
                {"start_datetime": {"$gte": start_datetime, "$lt": end_datetime}},
                {"start_datetime": {"$lte": start_datetime}, "end_datetime": {"$gte": end_datetime}}
            ]
        }
    });

    const booked_rooms_ids = await fetchBookedRoomsIds(query_conditions);

    const available_rooms = all_rooms.filter(({ _id }: any) => {
        // Compare ObjectIds
        return booked_rooms_ids.find((booked_room_id: any) => booked_room_id.equals(_id)) === undefined;
    }).map(({ name, type, link, coordinates }: any) => {
        return { name, type, link, coordinates };
    }) as any[];

    if (!coordinates) return res.status(200).json(available_rooms);

    const sorted_rooms = await sortRoomsByDistance(available_rooms, coordinates);
    return res.status(200).json(sorted_rooms);
}

export const getSoonestBookings = async (req: Request, res: Response) => {

    const { after_date } = req.body;
    if (!after_date) return res.status(400).json({ message: "Missing after_date" });

    // after_date must be a valid date
    const after_date_obj = new Date(after_date);
    if (after_date_obj.toString() === "Invalid Date") return res.status(400).json({ message: "Invalid after_date" });
    
    const soonest_booking_per_room = await fetchSoonestBookingsPerRoom(after_date_obj);

    const rooms = await fetchRooms();

    const rooms_with_soonest_booking = rooms.map((room: any) => {
        if (!(room._id.toString() in soonest_booking_per_room)) return room;
        const soonest_booking = soonest_booking_per_room[room._id.toString()];
        const { name } = room;
        return { name, soonest_booking };
    })

    return res.status(200).json(rooms_with_soonest_booking);
}
