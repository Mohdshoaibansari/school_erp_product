import { useState } from 'react';
import { Table, Button, Modal, TextInput, Select, Group, Loader, Badge } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function Users() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [institutionId, setInstitutionId] = useState('');
  const [roleId, setRoleId] = useState('');

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/v1/users').then(r => r.data),
  });

  const { data: categories } = useQuery({
    queryKey: ['user-categories'],
    queryFn: () => api.get('/v1/lookups/user-categories').then(r => r.data),
  });

  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => api.get('/v1/lookups/roles').then(r => r.data),
  });

  const { data: institutions } = useQuery({
    queryKey: ['institutions'],
    queryFn: () => api.get('/v1/institutions').then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: async (d: any) => {
      const userRes = await api.post('/v1/users', d);
      return userRes.data;
    },
    onSuccess: async (data: any) => {
      // Assign role if selected
      if (roleId) {
        await api.post(`/v1/users/${data.id}/roles`, { role_id: roleId });
      }
      qc.invalidateQueries({ queryKey: ['users'] });
      setModalOpen(false);
      notifications.show({ message: 'User created! They will receive an invite email.', color: 'green' });
    },
    onError: (err: any) => {
      notifications.show({ message: err.response?.data?.detail || 'Failed', color: 'red' });
    },
  });

  const transitionMut = useMutation({
    mutationFn: ({ id, state, reason }: any) => api.post(`/v1/users/${id}/transition`, { new_state: state, reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      notifications.show({ message: 'User status updated!', color: 'green' });
    },
  });

  const handleCreate = () => {
    createMut.mutate({
      email,
      name,
      user_category_id: categoryId,
      institution_id: institutionId,
    });
  };

  const statusColor = (s: string) => {
    if (s === 'active') return 'green';
    if (s === 'invited') return 'blue';
    if (s === 'suspended') return 'red';
    if (s === 'archived') return 'gray';
    return 'yellow';
  };

  if (isLoading) return <Loader />;

  return (
    <>
      <Group mb="md">
        <Button onClick={() => setModalOpen(true)}>+ New User</Button>
      </Group>

      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Email</Table.Th>
            <Table.Th>Category</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Institution</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(users || []).map((u: any) => (
            <Table.Tr key={u.id}>
              <Table.Td>{u.name}</Table.Td>
              <Table.Td>{u.email}</Table.Td>
              <Table.Td>{u.user_category_id?.slice(0, 8)}</Table.Td>
              <Table.Td><Badge color={statusColor(u.lifecycle_status)}>{u.lifecycle_status}</Badge></Table.Td>
              <Table.Td>{u.institution_id?.slice(0, 8)}</Table.Td>
              <Table.Td>
                <Group gap="xs">
                  {u.lifecycle_status === 'active' && (
                    <Button size="xs" color="red" onClick={() => transitionMut.mutate({ id: u.id, state: 'suspended', reason: 'Admin action' })}>Suspend</Button>
                  )}
                  {u.lifecycle_status === 'suspended' && (
                    <Button size="xs" color="green" onClick={() => transitionMut.mutate({ id: u.id, state: 'active', reason: 'Reactivated' })}>Reactivate</Button>
                  )}
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Create User" size="lg">
        <TextInput label="Name" value={name} onChange={e => setName(e.target.value)} mb="sm" />
        <TextInput label="Email" value={email} onChange={e => setEmail(e.target.value)} mb="sm" />
        <Select
          label="User Category"
          data={(categories || []).map((c: any) => ({ value: c.id, label: c.name }))}
          value={categoryId}
          onChange={v => setCategoryId(v || '')}
          mb="sm"
        />
        <Select
          label="Institution"
          data={(institutions || []).map((i: any) => ({ value: i.id, label: i.display_name }))}
          value={institutionId}
          onChange={v => setInstitutionId(v || '')}
          mb="sm"
        />
        <Select
          label="Role"
          data={(roles || []).map((r: any) => ({ value: r.id, label: r.name }))}
          value={roleId}
          onChange={v => setRoleId(v || '')}
          mb="sm"
        />
        <Button fullWidth onClick={handleCreate} loading={createMut.isPending}>Create User</Button>
      </Modal>
    </>
  );
}
