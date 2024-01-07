import { Router, Request, Response } from 'express';
import { getRooms, getRoom, getAvailableRooms } from '../controllers/rooms';

const router = Router();

router.get('/', (req: Request, res: Response) => {
    return getRooms(req, res);
});

router.get('/:room_name', (req: Request, res: Response) => {
    return getRoom(req, res);
});

router.post('/find_free_rooms', (req: Request, res: Response) => {
    return getAvailableRooms(req, res);
})

export default router;
