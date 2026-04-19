import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { confirmMockPayment } from "../api/payments";

export default function MockPay() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const bookingId = searchParams.get("booking_id") ?? "";
  const [submitting, setSubmitting] = useState<"pay" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handle = async (success: boolean) => {
    if (!id) return;
    setSubmitting(success ? "pay" : "cancel");
    setError(null);
    try {
      await confirmMockPayment(id, success);
      navigate(`/booking/payment-result?booking_id=${bookingId}`);
    } catch (err) {
      setError(
        (err as { response?: { data?: { detail?: string } }; message?: string })
          ?.response?.data?.detail ??
          (err as { message?: string })?.message ??
          "Thanh toán thất bại",
      );
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="card narrow center">
      <h1>Thanh toán mô phỏng</h1>
      <p className="muted">Mã thanh toán: {id}</p>
      {bookingId && <p className="muted">Mã đơn: {bookingId}</p>}
      <div className="btn-row">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => handle(true)}
          disabled={submitting !== null}
        >
          {submitting === "pay" ? "Đang xử lý…" : "Thanh toán"}
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => handle(false)}
          disabled={submitting !== null}
        >
          {submitting === "cancel" ? "Đang hủy…" : "Hủy"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
