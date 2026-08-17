import { NavLink, Stack, Tooltip, Center, Divider, Box } from '@mantine/core';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { navItemsForRoles } from '../core/access/navConfig';
import { useSession } from '../core/auth/useSession';

export function Sidebar({
  onNavigate,
  collapsed = false,
  onToggleCollapse,
}: {
  onNavigate?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}) {
  const { user } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const items = navItemsForRoles(user?.roles ?? []);

  return (
    <Stack gap={4} p="sm" style={{ height: '100%', justifyContent: 'space-between' }}>
      <Box>
        {items.map((item) =>
          collapsed ? (
            <Tooltip key={item.path} label={item.label} position="right" withinPortal>
              <NavLink
                label=""
                active={location.pathname.startsWith(item.path)}
                onClick={() => {
                  navigate(item.path);
                  onNavigate?.();
                }}
                variant="filled"
                style={{ justifyContent: 'center' }}
                leftSection={
                  <Center
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      backgroundColor: location.pathname.startsWith(item.path)
                        ? 'var(--mantine-color-blue-6)'
                        : 'var(--mantine-color-gray-3)',
                      color: location.pathname.startsWith(item.path)
                        ? '#fff'
                        : 'var(--mantine-color-dark-6)',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {item.label[0]}
                  </Center>
                }
              />
            </Tooltip>
          ) : (
            <NavLink
              key={item.path}
              label={item.label}
              active={location.pathname.startsWith(item.path)}
              onClick={() => {
                navigate(item.path);
                onNavigate?.();
              }}
              variant="filled"
            />
          ),
        )}
      </Box>
      {onToggleCollapse ? (
        <>
          <Divider />
          <NavLink
            label={collapsed ? '' : 'Collapse'}
            onClick={onToggleCollapse}
            variant="subtle"
            style={{ justifyContent: collapsed ? 'center' : undefined }}
            leftSection={
              collapsed ? (
                <ChevronRight size={18} />
              ) : (
                <ChevronLeft size={18} />
              )
            }
          />
        </>
      ) : null}
    </Stack>
  );
}
