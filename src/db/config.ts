import mongoose from "mongoose";

const DB_USER = process.env.DB_USER;
const DB_PASSWORD = process.env.DB_PASSWORD;
const DB_NAME = process.env.DB_NAME;
const DB_URL = process.env.DB_URL;

export default () => {
    // connect to MongoDB
    mongoose.connect(`mongodb+srv://${DB_USER}:${DB_PASSWORD}@${DB_URL}/${DB_NAME}?retryWrites=true&w=majority`).then(() => {
        console.log('Connected to MongoDB');
    }).catch((err) => {
        console.error(err);
    })
}