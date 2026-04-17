import apiClient from "./client";

export type MockPayResponse = {
  status: string;
  message?: string;
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
