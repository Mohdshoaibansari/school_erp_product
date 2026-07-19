import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { AppShell, Group, Button, Title, Tabs } from '@mantine/core';

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const token = localStorage.getItem('access_token');
  if (!token) { window.location.href = '/login'; return null; }

  const logout = () => { localStorage.clear(); window.location.href = '/login'; };

  const isPlatform = location.pathname.startsWith('/platform');
  const isFees = location.pathname.startsWith('/fees');
  const isHW = location.pathname.startsWith('/homework');

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Title order={4}>School ERP — Test UI</Title>
            <Button variant={isPlatform ? 'filled' : 'outline'} onClick={() => navigate('/platform/clients')}>Platform</Button>
            <Button variant={isFees ? 'filled' : 'outline'} onClick={() => navigate('/fees')}>Fees</Button>
            <Button variant={isHW ? 'filled' : 'outline'} onClick={() => navigate('/homework')}>Homework</Button>
          </Group>
          <Button color="red" onClick={logout}>Logout</Button>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {isPlatform && (
          <Tabs value={location.pathname} onChange={(v) => v && navigate(v)} mb="md">
            <Tabs.List>
              <Tabs.Tab value="/platform/clients">Clients</Tabs.Tab>
              <Tabs.Tab value="/platform/institutions">Institutions</Tabs.Tab>
              <Tabs.Tab value="/platform/users">Users</Tabs.Tab>
            </Tabs.List>
          </Tabs>
        )}
        {isFees && (
          <Tabs value={location.pathname} onChange={(v) => v && navigate(v)} mb="md">
            <Tabs.List>
              <Tabs.Tab value="/fees">Fee Types</Tabs.Tab>
              <Tabs.Tab value="/fees/assignments">Assignments</Tabs.Tab>
              <Tabs.Tab value="/fees/payments">Payments</Tabs.Tab>
            </Tabs.List>
          </Tabs>
        )}
        {isHW && (
          <Tabs value={location.pathname} onChange={(v) => v && navigate(v)} mb="md">
            <Tabs.List>
              <Tabs.Tab value="/homework">Homeworks</Tabs.Tab>
              <Tabs.Tab value="/homework/grades">Grades</Tabs.Tab>
            </Tabs.List>
          </Tabs>
        )}
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
