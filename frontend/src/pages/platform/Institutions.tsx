import { useState } from 'react';
import { Table, Button, Modal, TextInput, Select, Group, Loader, Badge } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function Institutions() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [instTypeId, setInstTypeId] = useState('');

  const { data: institutions, isLoading } = useQuery({
    queryKey: ['institutions'],
    queryFn: () => api.get('/v1/institutions').then(r => r.data),
  });

  const { data: instTypes } = useQuery({
    queryKey: ['institution-types'],
    queryFn: () => api.get('/v1/platform/institution-types').then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/v1/institutions', d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['institutions'] });
      setModalOpen(false);
      notifications.show({ message: 'Institution created!', color: 'green' });
    },
    onError: (err: any) => {
      notifications.show({ message: err.response?.data?.detail || 'Failed', color: 'red' });
    },
  });

  const transitionMut = useMutation({
    mutationFn: ({ id, state }: any) => api.post(`/v1/institutions/${id}/transition`, { new_state: state }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['institutions'] });
      notifications.show({ message: 'Status updated!', color: 'green' });
    },
  });

  const handleCreate = () => {
    createMut.mutate({
      display_name: displayName,
      institution_type_id: instTypeId,
    });
  };

  const statusColor = (s: string) => {
    if (s === 'active') return 'green';
    if (s === 'suspended') return 'red';
    if (s === 'onboarding') return 'blue';
    return 'gray';
  };

  if (isLoading) return <Loader />;

  return (
    <>
      <Group mb="md">
        <Button onClick={() => setModalOpen(true)}>+ New Institution</Button>
      </Group>

      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Client ID</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(institutions || []).map((i: any) => (
            <Table.Tr key={i.id}>
              <Table.Td>{i.display_name}</Table.Td>
              <Table.Td><Badge color={statusColor(i.current_lifecycle_status)}>{i.current_lifecycle_status}</Badge></Table.Td>
              <Table.Td>{i.client_id?.slice(0, 8)}</Table.Td>
              <Table.Td>
                <Group gap="xs">
                  {i.current_lifecycle_status === 'onboarding' && (
                    <Button size="xs" color="green" onClick={() => transitionMut.mutate({ id: i.id, state: 'active' })}>Go Live</Button>
                  )}
                  {i.current_lifecycle_status === 'active' && (
                    <Button size="xs" color="red" onClick={() => transitionMut.mutate({ id: i.id, state: 'suspended' })}>Suspend</Button>
                  )}
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Create Institution">
        <TextInput label="Display Name" value={displayName} onChange={e => setDisplayName(e.target.value)} mb="sm" />
        <Select
          label="Institution Type"
          data={(instTypes || []).map((t: any) => ({ value: t.id, label: t.name || t.display_name }))}
          value={instTypeId}
          onChange={v => setInstTypeId(v || '')}
          mb="sm"
        />
        <Button fullWidth onClick={handleCreate} loading={createMut.isPending}>Create</Button>
      </Modal>
    </>
  );
}
