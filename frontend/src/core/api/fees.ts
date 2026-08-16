import { api } from './client';
import type {
  FeeAssignmentCreateDTO,
  FeeAssignmentDTO,
  FeeAssignmentUpdateDTO,
  FeeTypeCreateDTO,
  FeeTypeDTO,
  FeeTypeUpdateDTO,
  PaymentCreateDTO,
  PaymentDTO,
  WaiveDTO,
} from './dto/fees';

export const feesApi = {
  // Fee types
  listFeeTypes: (institutionId?: string) =>
    api.get<FeeTypeDTO[]>('/api/v1/fee-types', {
      params: institutionId ? { institution_id: institutionId } : {},
    }),
  getFeeType: (feeTypeId: string) =>
    api.get<FeeTypeDTO>(`/api/v1/fee-types/${feeTypeId}`),
  createFeeType: (payload: FeeTypeCreateDTO) =>
    api.post<FeeTypeDTO>('/api/v1/fee-types', payload),
  updateFeeType: (feeTypeId: string, payload: FeeTypeUpdateDTO) =>
    api.patch<FeeTypeDTO>(`/api/v1/fee-types/${feeTypeId}`, payload),
  deleteFeeType: (feeTypeId: string) =>
    api.delete(`/api/v1/fee-types/${feeTypeId}`),

  // Fee assignments
  listFeeAssignments: (filters?: {
    user_id?: string;
    status_filter?: string;
    overdue?: boolean;
  }) =>
    api.get<FeeAssignmentDTO[]>('/api/v1/fee-assignments', {
      params: filters ?? {},
    }),
  getFeeAssignment: (assignmentId: string) =>
    api.get<FeeAssignmentDTO>(`/api/v1/fee-assignments/${assignmentId}`),
  createFeeAssignments: (payload: FeeAssignmentCreateDTO) =>
    api.post<FeeAssignmentDTO[]>('/api/v1/fee-assignments', payload),
  updateFeeAssignment: (
    assignmentId: string,
    payload: FeeAssignmentUpdateDTO,
  ) =>
    api.patch<FeeAssignmentDTO>(
      `/api/v1/fee-assignments/${assignmentId}`,
      payload,
    ),
  waiveFeeAssignment: (assignmentId: string, payload: WaiveDTO) =>
    api.post<FeeAssignmentDTO>(
      `/api/v1/fee-assignments/${assignmentId}/waive`,
      payload,
    ),

  // Payments
  listPayments: (filters?: {
    fee_assignment_id?: string;
    user_id?: string;
  }) =>
    api.get<PaymentDTO[]>('/api/v1/payments', { params: filters ?? {} }),
  recordPayment: (payload: PaymentCreateDTO) =>
    api.post<PaymentDTO>('/api/v1/payments', payload),
};
