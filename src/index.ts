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

const allowedOrigins = [
    'https://occupancy.flep.ch',
    'https://antoninfaure.github.io',
    'https://lm.polysource.ch'
];

var corsOptions = {
    origin: function (origin: string, callback: Function) {
        console.log('Origin:', origin)
        if (allowedOrigins.indexOf(origin) !== -1) {
            // Allow requests with a valid origin
            return callback(null, true);
        } else {
            // Reject requests from unapproved origins
            return callback(null, false)
            //return callback(new Error('Origin not allowed'), false);
        }
    },
    methods: ['GET', 'PUT', 'POST', 'DELETE', 'OPTIONS'],
    optionsSuccessStatus: 200, // some legacy browsers (IE11, various SmartTVs) choke on 204
    credentials: true, //Credentials are cookies, authorization headers or TLS client certificates.
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'device-remember-token', 'Access-Control-Allow-Origin', 'Origin', 'Accept']
};

app.use(cors(corsOptions));

// Middleware to handle errors from CORS
app.use((err: any, req: any, res: any, next: any) => {
    if (err instanceof Error && err.message === 'Origin not allowed') {
        return res.status(403).json({ message: 'Origin not allowed' });
    }
    next(err);
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));


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
    console.log(`Environment: ${process.env.NODE_ENV}`)
});