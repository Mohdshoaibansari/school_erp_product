import { useState } from 'react';
import { Table, Button, Modal, TextInput, Group, Loader, Badge } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function Clients() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [slug, setSlug] = useState('');
  const [email, setEmail] = useState('');
  const [legalEntityType] = useState('81e77718-098b-45a0-a1ee-931441804ff8'); // Pvt Ltd default

  const { data: clients, isLoading } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.get('/v1/platform/clients').then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.post('/v1/platform/clients', d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      setModalOpen(false);
      notifications.show({ message: 'Client created!', color: 'green' });
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'object' ? JSON.stringify(detail) : detail || 'Failed';
      notifications.show({ message, color: 'red' });
    },
  });

  const transitionMut = useMutation({
    mutationFn: ({ id, state }: any) => api.post(`/v1/platform/clients/${id}/transition`, { new_state: state }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['clients'] });
      notifications.show({ message: 'Status updated!', color: 'green' });
    },
  });

  const handleCreate = () => {
    createMut.mutate({
      display_name: displayName,
      legal_name: legalName,
      slug,
      primary_contact_email: email,
      legal_entity_type_id: legalEntityType,
    });
  };

  const statusColor = (s: string) => {
    if (s === 'active') return 'green';
    if (s === 'suspended') return 'red';
    if (s === 'archived') return 'gray';
    return 'blue';
  };

  if (isLoading) return <Loader />;

  return (
    <>
      <Group mb="md">
        <Button onClick={() => setModalOpen(true)}>+ New Client</Button>
      </Group>

      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Slug</Table.Th>
            <Table.Th>Email</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(clients || []).map((c: any) => (
            <Table.Tr key={c.id}>
              <Table.Td>{c.display_name}</Table.Td>
              <Table.Td><Badge variant="outline">{c.slug}</Badge></Table.Td>
              <Table.Td>{c.primary_contact_email}</Table.Td>
              <Table.Td><Badge color={statusColor(c.current_lifecycle_status)}>{c.current_lifecycle_status}</Badge></Table.Td>
              <Table.Td>
                <Group gap="xs">
                  {c.current_lifecycle_status === 'active' && (
                    <Button size="xs" color="red" onClick={() => transitionMut.mutate({ id: c.id, state: 'suspended' })}>Suspend</Button>
                  )}
                  {c.current_lifecycle_status === 'suspended' && (
                    <Button size="xs" color="green" onClick={() => transitionMut.mutate({ id: c.id, state: 'active' })}>Reactivate</Button>
                  )}
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Create Client">
        <TextInput label="Display Name" value={displayName} onChange={e => setDisplayName(e.target.value)} mb="sm" />
        <TextInput label="Legal Name" value={legalName} onChange={e => setLegalName(e.target.value)} mb="sm" />
        <TextInput label="Slug (subdomain)" value={slug} onChange={e => setSlug(e.target.value)} mb="sm" placeholder="e.g., school-b" />
        <TextInput label="Contact Email" value={email} onChange={e => setEmail(e.target.value)} mb="sm" />
        <Button fullWidth onClick={handleCreate} loading={createMut.isPending}>Create</Button>
      </Modal>
    </>
  );
}
