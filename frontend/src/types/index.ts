export type AuthUser = {
  user_id: string;
  email: string;
  role: string;
};

export type AuthResponse = {
  access_token: string;
  user_id: string;
  email: string;
  role: string;
};

export type Showtime = {
  id: string;
  room: string;
  starts_at: string;
  base_price: number;
  movie_id?: string;
};

export type Movie = {
  id: string;
  title: string;
  description?: string;
  duration_minutes?: number;
  poster_url?: string;
  showtimes?: Showtime[];
};

export type SeatStatus = "AVAILABLE" | "PENDING" | "BOOKED";

export type Seat = {
  seat_number: string;
  status: SeatStatus;
};

export type VoucherResult = {
  valid: boolean;
  discount_amount: number;
  final_amount: number;
  message?: string;
};

export type Booking = {
  booking_id?: string;
  id?: string;
  user_id?: string;
  showtime_id?: string;
  seat_numbers?: string[];
  voucher_code?: string | null;
  status: string;
  final_amount?: number;
  payment_id?: string;
  payment_url?: string;
  workflow_id?: string;
  created_at?: string;
  email?: string;
};

export type CreateBookingResponse = {
  booking_id: string;
  payment_id: string;
  payment_url: string;
  status: string;
  final_amount: number;
  workflow_id: string;
};
