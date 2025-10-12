import axios from "axios";
const baseURL = import.meta.env.VITE_API_BASE || "http://localhost:5000/v1";
export const api = axios.create({ baseURL });
