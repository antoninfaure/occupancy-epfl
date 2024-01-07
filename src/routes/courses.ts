import { Router, Request, Response } from 'express';
import { getCourses, getCourse } from '../controllers/courses';

const router = Router();

router.get('/', (req: Request, res: Response) => {
    return getCourses(req, res);
});

router.get('/:code', (req: Request, res: Response) => {
    return getCourse(req, res)
});

export default router;
