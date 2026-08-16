import { Alert } from '@mantine/core';
import type { ApiError } from '../core/api/errors';

/**
 * Inline friendly permission-denied surface for action-level 403s. Never
 * renders a raw error or stack trace (R8, REQ-SHELL-07).
 */
export function PermissionDenied({ error }: { error?: ApiError }) {
  return (
    <Alert color="danger" title="You don't have permission for this action" mb="md">
      {error?.message ?? 'Your role does not allow this action.'}
    </Alert>
  );
}
