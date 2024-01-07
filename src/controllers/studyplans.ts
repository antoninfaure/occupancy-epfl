// controllers/studyplans.ts
import { Response, Request} from 'express';

import { fetchStudyplans, fetchStudyplan } from '../services/studyplans';
import { fetchStudyplanCourses } from '../services/courses';
import { fetchCoursesSchedules } from '../services/bookings';

export const getStudyplans = async (req: Request, res: Response) => {
    const studyplans = await fetchStudyplans();

    return res.status(200).json(studyplans);
}

export const getStudyplanById = async (req: Request, res: Response) => {
    const { id } = req.params;

    const studyplan = await fetchStudyplan(id);
    if (!studyplan) return res.status(404).json({ message: 'Studyplan not found' });

    // Fetch courses
    const courses = await fetchStudyplanCourses(studyplan._id);
    const parsedCourses = courses.map(({ _id, ...courseProps }: any) => { return { ...courseProps } });

    // Fetch courses' schedules
    const schedules = await fetchCoursesSchedules(courses.map(({ _id }: any) => _id));

    const result = {
        ...studyplan,
        schedules,
        courses: parsedCourses
    }

    return res.status(200).json(result);
}
