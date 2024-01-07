export interface Room {
    available: boolean;
    name: string;
    type: string;
    capacity?: number;
}

export interface Teacher {
    available: boolean;
    name: string;
    people_url: string;
}

export interface Course {
    available: boolean;
    name: string;
    code: string;
    credits: number;
    edu_url?: string;
    language?: string;
    teachers?: Teacher[];
}

export interface CourseSchedule {
    available: boolean;
    course_id: string;
    start_datetime: string;
    end_datetime: string;
    label: string;
}

export interface EventSchedule {
    available: boolean;
    start_datetime: string;
    end_datetime: string;
    label: string;
    name: string;
    description?: string;
}

export interface CourseBooking {
    available: boolean;
    room_id: string;
    schedule_id: string;
}

export interface EventBooking {
    available: boolean;
    room_id: string;
    schedule_id: string;
}

export interface Studyplan {
    available: boolean;
    unit_id: string;
    semester_id: string;
    semester?: Semester;
    unit?: Unit;
}

export interface PlannedIn {
    available: boolean;
    course_id: string;
    studyplan_id: string;
}

export interface Semester {
    available: boolean;
    name: string;
    start_date: string;
    end_date: string;
    type: string;
    skip_dates?: string[];
}

export interface Unit {
    available: boolean;
    name: string;
    code: string;
    section?: string;
    promo?: string;
}