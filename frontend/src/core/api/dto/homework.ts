/**
 * Typed DTOs mirroring the Homework business module backend
 * (business/homework/services/dtos.py). IDs, dates, and timestamps are
 * serialized as strings in JSON (never `any`).
 */

export interface HomeworkCreateDTO {
  title: string;
  description: string | null;
  subject_id: string | null;
  grade_level_id: string | null;
  section_id: string | null;
  due_date: string;
  max_score: number | null;
}

export interface HomeworkUpdateDTO {
  title?: string | null;
  description?: string | null;
  subject_id?: string | null;
  grade_level_id?: string | null;
  section_id?: string | null;
  due_date?: string | null;
  max_score?: number | null;
  status?: string | null;
}

export interface HomeworkDTO {
  id: string;
  client_id: string;
  institution_id: string;
  title: string;
  description: string | null;
  subject_id: string | null;
  grade_level_id: string | null;
  section_id: string | null;
  due_date: string;
  max_score: number | null;
  status: string; // active | closed | archived
  assigned_by: string | null;
  created_at: string;
  submission_count: number;
}

export interface SubmissionCreateDTO {
  homework_id: string;
  content: string;
}

export interface SubmissionDTO {
  id: string;
  client_id: string;
  institution_id: string;
  homework_id: string;
  student_id: string;
  content: string | null;
  status: string; // submitted | late | graded
  submitted_at: string;
  created_at: string;
  student_name: string | null;
}

export interface GradeCreateDTO {
  score: number;
  feedback: string | null;
}

export interface GradeUpdateDTO {
  score?: number | null;
  feedback?: string | null;
}

export interface GradeDTO {
  id: string;
  client_id: string;
  institution_id: string;
  submission_id: string;
  score: number;
  max_score: number | null;
  feedback: string | null;
  graded_by: string | null;
  graded_at: string;
  created_at: string;
}
