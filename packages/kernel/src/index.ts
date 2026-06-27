export { TenantService } from './tenant.service';
export type { CreateTenantInput } from './tenant.service';

export { IdentityService } from './identity.service';
export type { CreateUserInput } from './identity.service';

export { AcademicService } from './academic.service';
export type {
  CreateLevelDefInput,
  CreateLevelInstanceInput,
  AssignClassTeacherInput,
  AssignSubjectTeacherInput,
  PromoteStudentsInput,
} from './academic.service';

export { AuthorizationService } from './authorization.service';

export { SubscriptionService } from './subscription.service';
