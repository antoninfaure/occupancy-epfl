// services/studyplans.ts
import { match } from 'assert';
import { PlannedInModel, StudyplanModel } from '../db/models';
import { Types } from 'mongoose';

export const fetchStudyplans = async () => {
    /*
        Fetch all studyplans with semester with end_date > now
        - Inputs:
            - None
        - Outputs:
            - Array of studyplans (_id, unit, semester)
    */

    const studyplans = await StudyplanModel.find({
        available: true
    })
        .select(["-available"])
        .populate({
            path: 'unit',
            select: '-_id name section code promo'
        })
        .populate({
            path: 'semester',
            match: { end_date: { $gt: new Date() } },
            select: '-_id name type'
        })
        .lean().exec();
        
    // Remove null semesters
    const filteredStudyplans = studyplans.filter(({ semester }: any) => semester);

    // Remove unit_id and semester_id
    return filteredStudyplans.map(({ unit, semester, _id}: any) => {
        return {
            _id,
            unit,
            semester,
        }
    });
}


export const fetchCourseStudyplans = async (course_id: Types.ObjectId) => {
    /*
        Fetch all studyplans of a course
        - Inputs:
            - course_id
        - Outputs:
            - Array of studyplans (_id, unit, semester)
    */

    const studyplans = await PlannedInModel.find({
        course_id: course_id,
        available: true
    })
    .select(["-available"])
    .populate({
        path: 'studyplan',
        populate: [{
            path: 'unit'
        }, {
            path: 'semester',
            match: { 
                'end_date': { $gt: new Date() }
            }
        }]
    })
    .lean().exec();

    // Filter out any study plans where the semester didn't match (end_date < now)
    const filteredStudyplans = studyplans.filter(({ studyplan }: any) => studyplan.semester);

    return filteredStudyplans.map(({ studyplan }: any) => {
        const { unit, semester, _id } = studyplan;
        const { name: unit_name, section, code, promo } = unit;
        const { name: semester_name, type: semester_type } = semester;
        return {
            _id,
            unit: {
                name: unit_name,
                section,
                code,
                promo
            },
            semester: {
                name: semester_name,
                type: semester_type
            }
        }
    });
}

export const fetchStudyplan = async (studyplan_id: string) => {
    /*
        Fetch a studyplan by id
        - Inputs:
            - studyplan_id
        - Outputs:
            - Studyplan (_id, unit, semester)
    */

    const studyplan = await StudyplanModel.findOne({
        _id: studyplan_id,
        available: true
    })
    .select(["-available"])
    .populate('unit')
    .populate('semester')
    .lean().exec();

    if (!studyplan) return null;

    const { unit, semester, _id } = studyplan as any;
    const { name: unit_name, section, code, promo } = unit;
    const { name: semester_name, type: semester_type, skip_dates } = semester;

    return {
        _id,
        unit: {
            name: unit_name,
            section,
            code,
            promo
        },
        semester: {
            name: semester_name,
            type: semester_type,
            skip_dates
        }
    }   
}