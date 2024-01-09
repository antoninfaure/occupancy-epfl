import express, {
    Request,
    Response
} from 'express';

require('dotenv').config();

// cors
var cors = require('cors');

import db_init from './db/config';

db_init()

// ROUTES
import routerRooms from './routes/rooms';
import routerCourses from './routes/courses'
import routerStudyplans from './routes/studyplans';

const app = express();
const port = process.env.PORT || 5000;

// MIDDLEWARE

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

if (process.env.NODE_ENV === 'production') {
    app.use(cors({
        origin: [
            'https://occupancy.flep.ch',
            'https://antoninfaure.github.io',
            'https://lm.polysource.ch'
        ]
    }));
} else {
    app.use(cors());
}

// ROUTES
app.use('/api/rooms', routerRooms);
app.use('/api/courses', routerCourses)
app.use('/api/studyplans', routerStudyplans);


// Add 404 handler
app.use(function (_req: Request, res: Response) {
    res.status(404).send("Not found");
});

app.listen(port, () => {
    console.log(`Listening on port ${port}`);
});