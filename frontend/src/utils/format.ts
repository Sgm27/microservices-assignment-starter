export function formatVND(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "0 đ";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "0 đ";
  return `${Math.round(n).toLocaleString("vi-VN")} đ`;
}

export function formatDateVi(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

const STATUS_LABELS: Record<string, string> = {
  PENDING: "Đang chờ",
  ACTIVE: "Hoàn tất",
  CONFIRMED: "Đã xác nhận",
  SUCCESS: "Thành công",
  FAILED: "Thất bại",
  CANCELLED: "Đã hủy",
  AVAILABLE: "Còn trống",
  BOOKED: "Đã đặt",
  AWAITING_PAYMENT: "Chờ thanh toán",
};

export function statusLabel(status: string | undefined | null): string {
  if (!status) return "";
  return STATUS_LABELS[status.toUpperCase()] ?? status;
}
