import apiClient from "./client";

export type MockPayResponse = {
  status: string;
  message?: string;
};

export type PaymentDetail = {
  id: number;
  booking_id: number;
  amount: number | string;
  status: string;
  provider?: string | null;
  payment_url?: string | null;
  provider_txn_id?: string | null;
};

export async function confirmMockPayment(
  paymentId: string,
  success: boolean,
): Promise<MockPayResponse> {
  const { data } = await apiClient.post<MockPayResponse>(
    `/payments/mock/${paymentId}/confirm`,
    { success },
  );
  return data;
}

export async function getPayment(paymentId: string): Promise<PaymentDetail> {
  const { data } = await apiClient.get<PaymentDetail>(`/payments/${paymentId}`);
  return data;
}
