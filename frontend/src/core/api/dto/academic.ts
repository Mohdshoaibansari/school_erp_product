/**
 * Typed DTOs mirroring the C-05 academic structure backend
 * (kernel/academic/services/dtos.py). IDs, dates, and timestamps are
 * serialized as strings in JSON.
 */

export interface AcademicYearCreateDTO {
  name: string;
  start_date: string;
  end_date: string;
  clone_from: string | null;
}

export interface AcademicYearTransitionDTO {
  new_state: string;
  reason: string | null;
}

export interface AcademicYearDTO {
  id: string;
  client_id: string;
  institution_id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: string; // planning | active | closed
  created_at: string;
  updated_at: string;
}

export interface TermDTO {
  id: string;
  academic_year_id: string;
  name: string;
  start_date: string;
  end_date: string;
  sort_order: number;
}

export interface GradeLevelDTO {
  id: string;
  academic_year_id: string;
  name: string;
  sort_order: number;
}

export interface ClassDTO {
  id: string;
  academic_year_id: string;
  grade_level_id: string;
  name: string;
  sort_order: number;
}

export interface SectionDTO {
  id: string;
  academic_year_id: string;
  class_id: string;
  name: string;
  homeroom_teacher_id: string | null;
  sort_order: number;
}

export interface SubjectDTO {
  id: string;
  academic_year_id: string;
  name: string;
  code: string | null;
  sort_order: number;
}

export interface SubjectGroupDTO {
  id: string;
  name: string;
}

export interface StudentEnrollmentCreateDTO {
  student_id: string;
  section_id: string;
}

export interface StudentEnrollmentDTO {
  id: string;
  academic_year_id: string;
  student_id: string;
  section_id: string;
  enrolled_at: string;
  status: string; // active | transferred | withdrawn | archived
}

export interface TeacherAssignmentCreateDTO {
  teacher_id: string;
  section_id: string;
  subject_id: string;
}

export interface TeacherAssignmentDTO {
  id: string;
  academic_year_id: string;
  teacher_id: string;
  section_id: string;
  subject_id: string;
  status: string; // active | inactive | archived
}

export interface AcademicStructureDTO {
  academic_year: AcademicYearDTO;
  terms: TermDTO[];
  grade_levels: GradeLevelDTO[];
  classes: ClassDTO[];
  sections: SectionDTO[];
  subjects: SubjectDTO[];
}
