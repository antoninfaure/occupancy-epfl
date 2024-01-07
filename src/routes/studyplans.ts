// routes/studyplans.ts
import { Router, Request, Response } from 'express';
import { getStudyplans, getStudyplanById } from '../controllers/studyplans';

const router = Router();

router.get('/', (req: Request, res: Response) => {
    return getStudyplans(req, res);
});

router.get('/:id', (req: Request, res: Response) => {
    return getStudyplanById(req, res);
});

export default router;