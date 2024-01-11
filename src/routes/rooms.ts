import { Router, Request, Response } from 'express';
import { getRooms, getRoom, getAvailableRooms, getSoonestBookings } from '../controllers/rooms';

const router = Router();

router.get('/', (req: Request, res: Response) => {
    return getRooms(req, res);
});

router.post('/find_free_rooms', (req: Request, res: Response) => {
    return getAvailableRooms(req, res);
})

router.post('/find_soonest_bookings', (req: Request, res: Response) => {
    return getSoonestBookings(req, res);
})


router.get('/:room_name', (req: Request, res: Response) => {
    return getRoom(req, res);
});




export default router;
