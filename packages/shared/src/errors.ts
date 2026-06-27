export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NotFoundError';
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class StudentLimitExceededError extends Error {
  constructor(limit: number) {
    super(`Student limit reached (${limit}). Please upgrade your subscription.`);
    this.name = 'StudentLimitExceededError';
  }
}

export class ModuleNotEnabledError extends Error {
  constructor(moduleName: string) {
    super(`The ${moduleName} module is not enabled for this school.`);
    this.name = 'ModuleNotEnabledError';
  }
}

export class UnauthorizedError extends Error {
  constructor(message = 'You do not have permission to perform this action.') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}
