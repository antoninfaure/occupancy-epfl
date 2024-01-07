// controllers/rooms.ts
import { Response, Request} from 'express';

import { fetchRooms, fetchRoom, fetchBookedRoomsIds } from "../services/rooms";
import { fetchRoomCourseSchedules, fetchRoomEventSchedules } from "../services/bookings";

export const getRooms = async (req: Request, res: Response) => {
    const rooms = await fetchRooms();
    
    return res.status(200).json(rooms);
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
    const { name, type } = room
    const result = {
        name,
        type,
        schedules: course_schedules.concat(event_schedules)
    }
    
    return res.status(200).json(result);
}

export const getAvailableRooms = async (req: Request, res: Response) => {
    const { selection } = req.body;

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

    const all_rooms = await fetchRooms();
    
    if (selection.length === 0) return res.status(200).json(all_rooms);

    const datetime_ranges = selection.map(({ start, end }: any) => {
        const start_datetime = new Date(start);
        const end_datetime = new Date(end);
        return { start_datetime, end_datetime };
    });

    const query_conditions = datetime_ranges.map(({ start_datetime, end_datetime }: any) => {
        return {
            $or: [
                { start_datetime: { $lt: end_datetime }, end_datetime: { $gt: start_datetime } },
                { start_datetime: { $gte: start_datetime, $lt: end_datetime } },
                { start_datetime: { $lte: start_datetime }, end_datetime: { $gte: end_datetime } }
            ]
        }
    });

    const booked_rooms_ids = await fetchBookedRoomsIds(query_conditions);

    const available_rooms = all_rooms.filter(({ _id }: any) => !booked_rooms_ids.includes(_id));


    return res.status(200).json(available_rooms);
}