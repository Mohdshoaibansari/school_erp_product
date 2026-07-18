import { useState } from 'react';
import { Table, Button, Modal, TextInput, NumberInput, Group, Loader, Badge } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function FeeTypes() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [amount, setAmount] = useState<number>(0);
  const [instId, setInstId] = useState('');

  const { data: types, isLoading } = useQuery({ queryKey: ['fee-types'], queryFn: () => api.get('/v1/fee-types').then(r => r.data) });
  const createMut = useMutation({ mutationFn: (d: any) => api.post('/v1/fee-types', d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['fee-types'] }); setModalOpen(false); notifications.show({ message: 'Created', color: 'green' }); } });
  const updateMut = useMutation({ mutationFn: ({ id, d }: any) => api.patch(`/v1/fee-types/${id}`, d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['fee-types'] }); setModalOpen(false); notifications.show({ message: 'Updated', color: 'green' }); } });
  const deleteMut = useMutation({ mutationFn: (id: string) => api.delete(`/v1/fee-types/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['fee-types'] }); notifications.show({ message: 'Deactivated', color: 'orange' }); } });

  const openCreate = () => { setEditId(null); setName(''); setDesc(''); setAmount(0); setModalOpen(true); };
  const openEdit = (ft: any) => { setEditId(ft.id); setName(ft.name); setDesc(ft.description || ''); setAmount(Number(ft.default_amount)); setInstId(ft.institution_id); setModalOpen(true); };
  const save = () => {
    const d = { name, description: desc, default_amount: amount, institution_id: instId };
    editId ? updateMut.mutate({ id: editId, d }) : createMut.mutate(d);
  };

  if (isLoading) return <Loader />;
  return (
    <>
      <Group mb="md"><Button onClick={openCreate}>+ New Fee Type</Button></Group>
      <Table striped>
        <Table.Thead><Table.Tr><Table.Th>Name</Table.Th><Table.Th>Amount</Table.Th><Table.Th>Active</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{(types || []).map((ft: any) => (
          <Table.Tr key={ft.id}>
            <Table.Td>{ft.name}</Table.Td>
            <Table.Td>₹{ft.default_amount}</Table.Td>
            <Table.Td><Badge color={ft.is_active ? 'green' : 'red'}>{ft.is_active ? 'Active' : 'Inactive'}</Badge></Table.Td>
            <Table.Td>
              <Group gap="xs">
                <Button size="xs" onClick={() => openEdit(ft)}>Edit</Button>
                <Button size="xs" color="red" onClick={() => deleteMut.mutate(ft.id)}>Deactivate</Button>
              </Group>
            </Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>
      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editId ? 'Edit Fee Type' : 'New Fee Type'}>
        <TextInput label="Name" value={name} onChange={(e) => setName(e.target.value)} mb="sm" />
        <TextInput label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} mb="sm" />
        <NumberInput label="Default Amount (₹)" value={amount} onChange={(v) => setAmount(Number(v) || 0)} mb="sm" />
        <TextInput label="Institution ID" value={instId} onChange={(e) => setInstId(e.target.value)} mb="sm" disabled={!!editId} />
        <Button fullWidth onClick={save} loading={createMut.isPending || updateMut.isPending}>Save</Button>
      </Modal>
    </>
  );
}
