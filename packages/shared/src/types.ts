export type UserRole = 'SUPER_ADMIN' | 'SCHOOL_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'ACCOUNTANT';

export type ModuleName = 'students' | 'attendance' | 'fees' | 'timetable' | 'exams';

export type TenantStatus = 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED';

export type UserStatus = 'INVITED' | 'ACTIVE' | 'SUSPENDED' | 'ARCHIVED';

export type StudentStatus = 'ACTIVE' | 'TRANSFERRED' | 'GRADUATED' | 'ARCHIVED';

export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'HALF_DAY';

export type AcademicYearStatus = 'DRAFT' | 'ACTIVE' | 'COMPLETED';

export interface PaginatedResult<T> {
  data: T[];
  total: number;
  skip: number;
  take: number;
}
