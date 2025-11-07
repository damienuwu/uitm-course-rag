import axios from "axios";

const api = axios.create({
  // ✅ Backend runs directly at root, not /api
  baseURL: "http://127.0.0.1:8000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

export default api;
