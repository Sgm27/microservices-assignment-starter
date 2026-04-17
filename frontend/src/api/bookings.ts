import apiClient from "./client";
import type { Booking, CreateBookingResponse } from "../types";

export type CreateBookingPayload = {
  user_id: string;
  showtime_id: string;
  seat_numbers: string[];
  voucher_code?: string | null;
  email: string;
};

export async function createBooking(
  payload: CreateBookingPayload,
): Promise<CreateBookingResponse> {
  const { data } = await apiClient.post<CreateBookingResponse>(
    "/bookings",
    payload,
  );
  return data;
}

export async function getBooking(id: string): Promise<Booking> {
  const { data } = await apiClient.get<Booking>(`/bookings/${id}`);
  return data;
}

export async function listUserBookings(userId: string): Promise<Booking[]> {
  const { data } = await apiClient.get<Booking[]>(`/bookings/user/${userId}`);
  return data;
}
