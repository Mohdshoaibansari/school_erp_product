import { api } from './client';
import type {
  GradeCreateDTO,
  GradeDTO,
  GradeUpdateDTO,
  HomeworkCreateDTO,
  HomeworkDTO,
  HomeworkUpdateDTO,
  SubmissionDTO,
} from './dto/homework';

export const homeworkApi = {
  // Homeworks
  listHomeworks: (filters?: {
    subject_id?: string;
    grade_level_id?: string;
    section_id?: string;
    status?: string;
  }) =>
    api.get<HomeworkDTO[]>('/api/v1/homeworks', { params: filters ?? {} }),
  getHomework: (hwId: string) =>
    api.get<HomeworkDTO>(`/api/v1/homeworks/${hwId}`),
  createHomework: (payload: HomeworkCreateDTO) =>
    api.post<HomeworkDTO>('/api/v1/homeworks', payload),
  updateHomework: (hwId: string, payload: HomeworkUpdateDTO) =>
    api.patch<HomeworkDTO>(`/api/v1/homeworks/${hwId}`, payload),
  closeHomework: (hwId: string) =>
    api.post<HomeworkDTO>(`/api/v1/homeworks/${hwId}/close`),

  // Submissions
  listSubmissions: (filters?: {
    homework_id?: string;
    student_id?: string;
    status?: string;
  }) =>
    api.get<SubmissionDTO[]>('/api/v1/submissions', { params: filters ?? {} }),
  getSubmission: (subId: string) =>
    api.get<SubmissionDTO>(`/api/v1/submissions/${subId}`),

  // Grades
  listGrades: (filters?: {
    submission_id?: string;
    homework_id?: string;
    student_id?: string;
  }) => api.get<GradeDTO[]>('/api/v1/grades', { params: filters ?? {} }),
  gradeSubmission: (subId: string, payload: GradeCreateDTO) =>
    api.post<GradeDTO>(`/api/v1/submissions/${subId}/grade`, payload),
  updateGrade: (gradeId: string, payload: GradeUpdateDTO) =>
    api.patch<GradeDTO>(`/api/v1/grades/${gradeId}`, payload),
};
