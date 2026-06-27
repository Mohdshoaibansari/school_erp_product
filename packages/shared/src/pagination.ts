import { PaginatedResult } from './types';

export function paginate<T>(data: T[], total: number, skip: number, take: number): PaginatedResult<T> {
  return { data, total, skip, take };
}
