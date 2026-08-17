import { Box, Center, Divider, Group, NavLink, Stack, Text, Tooltip, UnstyledButton } from '@mantine/core';
import { ChevronLeft, ChevronRight, LayoutDashboard, Users, Building2, GraduationCap, BookOpen, Settings2, Receipt, ClipboardCheck, Landmark, ArrowRightLeft } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { navItemsForRoles, type NavItem } from '../core/access/navConfig';
import { useSession } from '../core/auth/useSession';

const iconFor = (path: string) => {
  if (path.includes('clients')) return Landmark;
  if (path.includes('ownership')) return ArrowRightLeft;
  if (path.includes('institution')) return Building2;
  if (path.includes('users')) return Users;
  if (path.includes('academic')) return GraduationCap;
  if (path.includes('config')) return Settings2;
  if (path.includes('fees')) return Receipt;
  if (path.includes('homework')) return ClipboardCheck;
  return BookOpen;
};

const groupFor = (item: NavItem) => {
  if (item.path.startsWith('/platform')) return 'Platform';
  if (item.path.startsWith('/institutions') || item.path === '/users') return 'People & Institutions';
  if (item.path.startsWith('/academic')) return 'Academics';
  if (item.path.startsWith('/fees') || item.path.startsWith('/student/fees')) return 'Finance';
  if (item.path.startsWith('/homework') || item.path.startsWith('/student/homework') || item.path.startsWith('/student/grades')) return 'Learning';
  if (item.path.startsWith('/parent')) return 'Family';
  if (item.path.startsWith('/config')) return 'Configuration';
  return 'Workspace';
};

export function Sidebar({ onNavigate, collapsed = false, onToggleCollapse }: { onNavigate?: () => void; collapsed?: boolean; onToggleCollapse?: () => void }) {
  const { user } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const items = navItemsForRoles(user?.roles ?? []);
  const groups = Array.from(new Set(items.map(groupFor)));

  const renderItem = (item: NavItem) => {
    const active = location.pathname.startsWith(item.path);
    const Icon = iconFor(item.path);
    const content = (
      <NavLink
        key={item.path}
        label={collapsed ? undefined : item.label}
        active={active}
        onClick={() => { navigate(item.path); onNavigate?.(); }}
        leftSection={<Icon size={18} strokeWidth={active ? 2.2 : 1.8} />}
        styles={{ root: { borderRadius: 12, marginBottom: 4, minHeight: 44, color: active ? '#fff' : '#CBD5E1', background: active ? 'linear-gradient(135deg, rgba(0,82,255,.95), rgba(77,124,255,.95))' : 'transparent', boxShadow: active ? '0 8px 20px rgba(0,82,255,.22)' : 'none' }, label: { fontWeight: active ? 600 : 500, fontSize: 13 }, section: { color: 'inherit' } }} />
    );
    return collapsed ? <Tooltip key={item.path} label={item.label} position="right" withinPortal>{content}</Tooltip> : content;
  };

  return (
    <Stack gap={0} p="sm" style={{ height: '100%', justifyContent: 'space-between' }}>
      <Box>
        <UnstyledButton onClick={() => navigate('/')} style={{ width: '100%', marginBottom: 22 }} aria-label="School ERP home">
          <GroupBrand collapsed={collapsed} />
        </UnstyledButton>
        {groups.map((group) => (
          <Box key={group} mb="lg">
            {!collapsed && <Text c="#64748B" size="10px" fw={700} tt="uppercase" px="sm" mb="xs" style={{ letterSpacing: '.14em', fontFamily: 'JetBrains Mono' }}>{group}</Text>}
            {items.filter((i) => groupFor(i) === group).map(renderItem)}
          </Box>
        ))}
      </Box>
      {onToggleCollapse ? (
        <>
          <Divider color="rgba(255,255,255,.10)" mb="sm" />
          <NavLink label={collapsed ? undefined : 'Collapse'} onClick={onToggleCollapse} leftSection={collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />} styles={{ root: { color: '#94A3B8', borderRadius: 12, minHeight: 44 }, label: { fontSize: 12 } }} />
        </>
      ) : null}
    </Stack>
  );
}

function GroupBrand({ collapsed }: { collapsed: boolean }) {
  return collapsed ? (
    <Center style={{ width: 42, height: 42, borderRadius: 14, background: 'linear-gradient(135deg,#0052FF,#4D7CFF)', color: '#fff', boxShadow: '0 10px 24px rgba(0,82,255,.28)' }}>
      <LayoutDashboard size={20} />
    </Center>
  ) : (
    <Stack gap={0} px="sm">
      <Group gap="sm" wrap="nowrap">
        <Center style={{ width: 40, height: 40, borderRadius: 14, background: 'linear-gradient(135deg,#0052FF,#4D7CFF)', color: '#fff', boxShadow: '0 10px 24px rgba(0,82,255,.28)' }}><LayoutDashboard size={20} /></Center>
        <div><Text c="white" fw={700} size="sm">School ERP</Text><Text c="#64748B" size="10px" tt="uppercase" style={{ letterSpacing: '.12em', fontFamily: 'JetBrains Mono' }}>Workspace</Text></div>
      </Group>
    </Stack>
  );
}
