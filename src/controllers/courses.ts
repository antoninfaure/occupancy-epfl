// controllers/courses.ts
import { Response, Request} from 'express';

import { fetchCourses, fetchCourse } from '../services/courses';
import { fetchCourseSchedules } from '../services/bookings';
import { fetchCourseStudyplans } from '../services/studyplans'

export const getCourses = async (req: Request, res: Response) => {
    const courses = await fetchCourses()

    const results = courses.map(({ course, studyplans } : any) => {
        // Set the semesterType as year if there is no fall or spring in the studyplans semester.type
        const semesterType = studyplans.reduce((acc: string, studyplan: any) => {
            if (studyplan.semester[0].type === 'fall' || studyplan.semester[0].type === 'spring') {
                return studyplan.semester[0].type
            }
            return acc
        }, 'year')

        // Flatten the course
        return {
            ...course,
            semesterType
        }
    })

    return res.status(200).json(results)
}

export const getCourse = async (req: Request, res: Response) => {
    const { code } = req.params

    const course = await fetchCourse(code)
    if (!course) return res.status(404).json({ message: 'Course not found' })

    const schedules = await fetchCourseSchedules(course._id)

    const studyplans = await fetchCourseStudyplans(course._id)

    const {
        _id,
        ...courseProps
    } = course
    

    const result = {
        ...courseProps,
        schedules,
        studyplans
    }

    return res.status(200).json(result)
}
