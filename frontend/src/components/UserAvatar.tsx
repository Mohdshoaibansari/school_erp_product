import { Avatar } from '@mantine/core';
import { bluePalette } from '../theme/tokens';

const SIZES = { sm: 28, md: 36, lg: 48 } as const;

/**
 * User avatar that derives initials from `name`.
 * First letter of the first name + first letter of the last name.
 * Falls back to the first letter if there is only one name token.
 */
export function UserAvatar({
  name,
  size = 'md',
  color,
}: {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}) {
  const parts = name.trim().split(/\s+/);
  const initials =
    parts.length >= 2
      ? `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
      : (parts[0]?.[0] ?? '?').toUpperCase();

  return (
    <Avatar
      size={SIZES[size]}
      radius="xl"
      color={color ?? bluePalette[6]}
    >
      {initials}
    </Avatar>
  );
}
