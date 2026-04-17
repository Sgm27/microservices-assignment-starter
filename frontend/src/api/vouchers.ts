import apiClient from "./client";
import type { VoucherResult } from "../types";

export async function validateVoucher(
  code: string,
  base_amount: number,
): Promise<VoucherResult> {
  const { data } = await apiClient.post<VoucherResult>("/vouchers/validate", {
    code,
    base_amount,
  });
  return data;
}
