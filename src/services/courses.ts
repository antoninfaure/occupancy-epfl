// services/courses.ts
import { CourseModel, PlannedInModel } from '../db/models';
import { Types } from 'mongoose';

export const fetchCourses = async () => {
    /*
        Fetch all courses
        - Inputs:
            - None
        - Outputs:
            - Array of courses (name, code, credits, teachers)
    */

    const courses = await PlannedInModel.aggregate([
        { $match: { available: true } },
        { 
            $group: {
                _id: "$course_id",
                studyplans: { $push: "$studyplan_id" }
            }
        },
        { 
            $lookup: {
                from: "courses",
                localField: "_id",
                foreignField: "_id",
                as: "course"
            }
        },
        { $unwind: "$course" },
        { 
            $project: { // Select fields of Course
                'course.name': 1,
                'course.code': 1,
                'course.credits': 1,
                studyplans: 1
            }
        },
        { 
            $lookup: {
                from: "studyplans",
                localField: "studyplans",
                foreignField: "_id",
                as: "studyplans"
            }
        },
        { 
            $unwind: "$studyplans" 
        },
        { 
            $lookup: {
                from: "semesters",
                localField: "studyplans.semester_id",
                foreignField: "_id",
                as: "studyplans.semester"
            }
        },
        { 
            $project: { // Select fields of Semester
                'studyplans.semester.type': 1,
                course: 1
            }
        },
        { 
            $group: {
                _id: "$_id",
                course: { $first: "$course" },
                studyplans: { $push: "$studyplans" }
            }
        }])
    
    return courses
}

export const fetchCourse = async (code: string) => {
    /*
        Fetch a course by code
        - Inputs:
            - code
        - Outputs:
            - Course (name, code, credits, teachers)
    */


    const course = await CourseModel.findOne({
        code,
        available: true
    })
    .select('-available')
    .populate('teachers')
    .lean().exec();

    if (!course) return null;

    if (!course.teachers || course.teachers.length === 0) return course;

    const { teachers, ...courseProps } = course;
    return {
        ...courseProps,
        teachers: teachers.map(({ name, people_url }: any) => { return { name, people_url } })
    }
}

export const fetchStudyplanCourses = async (studyplan_id: Types.ObjectId) => {
    /*
        Fetch all courses in a studyplan
        - Inputs:
            - studyplan_id
        - Outputs:
            - Array of courses (name, code, credits, teachers)
    */

    const courses = await PlannedInModel.find({
        studyplan_id: studyplan_id,
        available: true
    })
    .select(["-available"])
    .populate({
        path: 'course',
        populate: {
            path: 'teachers'
        },
    })
    .lean().exec();

    if (!courses || courses.length === 0) return [];

    return courses.map(({ course }: any) => {
        const { teachers, ...courseProps } = course;
        if (!teachers || teachers.length === 0) return {
            ...courseProps,
            teachers: []
        };
        return {
            ...courseProps,
            teachers: teachers.map(({ name, people_url }: any) => { return { name, people_url } })
        }
    });
}