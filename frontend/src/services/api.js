import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const fetchBookings = async () => {
    const response = await axios.get(`${API_BASE_URL}/bookings`);
    return response.data;
};

export const fetchDrivers = async () => {
    const response = await axios.get(`${API_BASE_URL}/drivers`);
    return response.data;
};

export const fetchState = async (phone) => {
    const response = await axios.get(`${API_BASE_URL}/state/${phone}`);
    return response.data;
};

export const driverAcceptBooking = async (driverId, bookingId) => {
    const response = await axios.post(`${API_BASE_URL}/driver/accept`, {
        driver_id: driverId,
        booking_id: bookingId
    });
    return response.data;
};

export const updateDriverLocation = async (driverId, bookingId, lat, lng) => {
    const response = await axios.post(`${API_BASE_URL}/driver/location`, {
        driver_id: driverId,
        booking_id: bookingId,
        lat: lat,
        lng: lng
    });
    return response.data;
};

export const verifyWeight = async (driverId, bookingId, verifiedWeight) => {
    const response = await axios.post(`${API_BASE_URL}/driver/verify-weight`, {
        driver_id: driverId,
        booking_id: bookingId,
        verified_weight: verifiedWeight
    });
    return response.data;
};
