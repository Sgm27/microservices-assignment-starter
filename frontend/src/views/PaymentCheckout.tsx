import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { confirmPayment, getPayment, type PaymentDetail } from "../api/payments";

export default function PaymentCheckout() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const bookingId = searchParams.get("booking_id") ?? "";
  const [submitting, setSubmitting] = useState<"pay" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [payment, setPayment] = useState<PaymentDetail | null>(null);

  useEffect(() => {
    if (!id) return;
    getPayment(id)
      .then(setPayment)
      .catch(() => {
        /* amount is decorative; ignore fetch errors */
      });
  }, [id]);

  const handle = async (success: boolean) => {
    if (!id) return;
    setSubmitting(success ? "pay" : "cancel");
    setError(null);
    try {
      await confirmPayment(id, success);
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

  const amountLabel = payment
    ? `${Number(payment.amount).toLocaleString("vi-VN")} VND`
    : "—";

  return (
    <div className="vnpay-checkout">
      <div className="vnpay-checkout__card">
        <div className="vnpay-checkout__header">VNPay — Cổng thanh toán</div>
        <div className="vnpay-checkout__body">
          <div className="vnpay-checkout__amount">
            <div className="vnpay-checkout__amount-label">Số tiền cần thanh toán</div>
            <div className="vnpay-checkout__amount-value">{amountLabel}</div>
          </div>
          <div className="vnpay-checkout__qr">
            <img src="/vnpay-qr.png" alt="VNPay QR Code" />
          </div>
          <p className="vnpay-checkout__hint">
            Quét mã QR bằng ứng dụng ngân hàng để thanh toán
          </p>
          <div className="vnpay-checkout__actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handle(true)}
              disabled={submitting !== null}
            >
              {submitting === "pay" ? "Đang xử lý…" : "Đã thanh toán"}
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
          <div className="vnpay-checkout__meta">
            Payment ID: {id}
            {bookingId && ` · Booking ID: ${bookingId}`}
          </div>
        </div>
      </div>
    </div>
  );
}
