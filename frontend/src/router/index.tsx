import { Navigate, Route, Routes } from "react-router-dom";
import PrivateRoute from "../components/PrivateRoute";
import Login from "../views/Login";
import MovieList from "../views/MovieList";
import MovieDetail from "../views/MovieDetail";
import ShowtimeBooking from "../views/ShowtimeBooking";
import MockPay from "../views/MockPay";
import PaymentResult from "../views/PaymentResult";
import MyBookings from "../views/MyBookings";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<MovieList />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route
        path="/showtimes/:id/book"
        element={
          <PrivateRoute>
            <ShowtimeBooking />
          </PrivateRoute>
        }
      />
      <Route
        path="/mock-pay/:id"
        element={
          <PrivateRoute>
            <MockPay />
          </PrivateRoute>
        }
      />
      <Route
        path="/booking/payment-result"
        element={
          <PrivateRoute>
            <PaymentResult />
          </PrivateRoute>
        }
      />
      <Route
        path="/bookings"
        element={
          <PrivateRoute>
            <MyBookings />
          </PrivateRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
