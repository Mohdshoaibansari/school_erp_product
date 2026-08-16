import { api } from './client';
import type {
  AcademicStructureDTO,
  AcademicYearCreateDTO,
  AcademicYearDTO,
  AcademicYearTransitionDTO,
  StudentEnrollmentCreateDTO,
  StudentEnrollmentDTO,
  SubjectDTO,
  SubjectGroupDTO,
  TeacherAssignmentCreateDTO,
  TeacherAssignmentDTO,
} from './dto/academic';

export const academicApi = {
  // Academic years
  createAcademicYear: (payload: AcademicYearCreateDTO) =>
    api.post<AcademicYearDTO>('/api/v1/academic-years', payload),
  listAcademicYears: (statusFilter?: string) =>
    api.get<AcademicYearDTO[]>('/api/v1/academic-years', {
      params: statusFilter ? { status_filter: statusFilter } : {},
    }),
  getAcademicYear: (yearId: string) =>
    api.get<AcademicYearDTO>(`/api/v1/academic-years/${yearId}`),
  transitionAcademicYear: (
    yearId: string,
    payload: AcademicYearTransitionDTO,
  ) =>
    api.post<AcademicYearDTO>(
      `/api/v1/academic-years/${yearId}/transition`,
      payload,
    ),
  getStructure: (yearId: string) =>
    api.get<AcademicStructureDTO>(
      `/api/v1/academic-years/${yearId}/structure`,
    ),

  // Subjects + subject groups (read-only lookups; generated via clone/template)
  listSubjects: (academicYearId?: string) =>
    api.get<SubjectDTO[]>('/api/v1/subjects', {
      params: academicYearId ? { academic_year_id: academicYearId } : {},
    }),
  listSubjectGroups: () =>
    api.get<SubjectGroupDTO[]>('/api/v1/subject-groups'),

  // Teacher assignments
  listTeacherAssignments: (filters?: {
    section_id?: string;
    teacher_id?: string;
    academic_year_id?: string;
  }) =>
    api.get<TeacherAssignmentDTO[]>('/api/v1/teacher-assignments', {
      params: filters ?? {},
    }),
  createTeacherAssignment: (payload: TeacherAssignmentCreateDTO) =>
    api.post<TeacherAssignmentDTO>('/api/v1/teacher-assignments', payload),
  removeTeacherAssignment: (assignmentId: string) =>
    api.delete(`/api/v1/teacher-assignments/${assignmentId}`),

  // Enrollments
  listEnrollments: (sectionId: string) =>
    api.get<StudentEnrollmentDTO[]>(
      `/api/v1/sections/${sectionId}/enrollments`,
    ),
  enrollStudent: (sectionId: string, payload: StudentEnrollmentCreateDTO) =>
    api.post<StudentEnrollmentDTO>(
      `/api/v1/sections/${sectionId}/enrollments`,
      payload,
    ),
  removeEnrollment: (enrollmentId: string) =>
    api.delete(`/api/v1/enrollments/${enrollmentId}`),
};
