/**
 * Typed DTOs mirroring the Fees business module backend
 * (business/fees/services/dtos.py). IDs, dates, timestamps, and Decimal money
 * values are serialized as strings in JSON (never `any`).
 */

export interface FeeTypeCreateDTO {
  name: string;
  description: string | null;
  default_amount: string; // Decimal → string
  institution_id: string;
}

export interface FeeTypeUpdateDTO {
  name?: string | null;
  description?: string | null;
  default_amount?: string | null;
  is_active?: boolean | null;
}

export interface FeeTypeDTO {
  id: string;
  client_id: string;
  institution_id: string;
  name: string;
  description: string | null;
  default_amount: string; // Decimal → string
  is_active: boolean;
  created_at: string;
}

export interface FeeAssignmentCreateDTO {
  fee_type_id: string;
  amount: string; // Decimal → string
  due_date: string;
  term_id: string | null;
  user_ids: string[];
  institution_id?: string | null;
  notes: string | null;
}

export interface FeeAssignmentUpdateDTO {
  amount?: string | null;
  due_date?: string | null;
  term_id?: string | null;
  notes?: string | null;
  status?: string | null;
}

export interface WaiveDTO {
  reason: string;
}

export interface FeeAssignmentDTO {
  id: string;
  client_id: string;
  institution_id: string;
  user_id: string;
  fee_type_id: string;
  amount: string; // Decimal → string
  due_date: string;
  term_id: string | null;
  status: string; // pending | partial | paid | overdue | waived
  assigned_by: string | null;
  notes: string | null;
  created_at: string;
  total_paid: string; // Decimal → string
}

export interface PaymentCreateDTO {
  fee_assignment_id: string;
  amount: string; // Decimal → string
  payment_method: string;
  payment_date?: string | null;
  reference_number?: string | null;
  notes?: string | null;
}

export interface PaymentDTO {
  id: string;
  client_id: string;
  institution_id: string;
  fee_assignment_id: string;
  amount: string; // Decimal → string
  payment_date: string;
  payment_method: string;
  receipt_number: string | null;
  reference_number: string | null;
  recorded_by: string | null;
  notes: string | null;
  created_at: string;
}
