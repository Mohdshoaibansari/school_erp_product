import { useState } from 'react';
import { Table, Button, Modal, TextInput, NumberInput, Badge, Group, Loader, Select, Textarea } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function FeeAssignments() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [feeTypeId, setFeeTypeId] = useState('');
  const [amount, setAmount] = useState<number>(0);
  const [dueDate, setDueDate] = useState('');
  const [userIds, setUserIds] = useState('');
  const [term, setTerm] = useState('');
  const [waiveModal, setWaiveModal] = useState(false);
  const [waiveId, setWaiveId] = useState('');
  const [waiveReason, setWaiveReason] = useState('');

  const { data: types } = useQuery({ queryKey: ['fee-types'], queryFn: () => api.get('/v1/fee-types').then(r => r.data) });
  const { data: assignments, isLoading } = useQuery({ queryKey: ['fee-assignments'], queryFn: () => api.get('/v1/fee-assignments').then(r => r.data) });
  const createMut = useMutation({ mutationFn: (d: any) => api.post('/v1/fee-assignments', d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['fee-assignments'] }); setModalOpen(false); notifications.show({ message: 'Assigned', color: 'green' }); } });
  const waiveMut = useMutation({ mutationFn: ({ id, reason }: any) => api.post(`/v1/fee-assignments/${id}/waive`, { reason }), onSuccess: () => { qc.invalidateQueries({ queryKey: ['fee-assignments'] }); setWaiveModal(false); notifications.show({ message: 'Waived', color: 'orange' }); } });

  const assignBulk = () => {
    const ids = userIds.split(',').map(s => s.trim()).filter(Boolean);
    createMut.mutate({ fee_type_id: feeTypeId, amount, due_date: dueDate, academic_term: term, user_ids: ids });
  };

  const statusColor = (s: string) => s === 'paid' ? 'green' : s === 'partial' ? 'yellow' : s === 'overdue' ? 'red' : s === 'waived' ? 'gray' : 'blue';

  if (isLoading) return <Loader />;
  return (
    <>
      <Group mb="md"><Button onClick={() => setModalOpen(true)}>+ New Assignment</Button></Group>
      <Table striped>
        <Table.Thead><Table.Tr><Table.Th>Student</Table.Th><Table.Th>Amount</Table.Th><Table.Th>Due</Table.Th><Table.Th>Status</Table.Th><Table.Th>Paid</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{(assignments || []).map((fa: any) => (
          <Table.Tr key={fa.id}>
            <Table.Td>{fa.user_id?.slice(0, 8)}</Table.Td>
            <Table.Td>₹{fa.amount}</Table.Td>
            <Table.Td>{fa.due_date}</Table.Td>
            <Table.Td><Badge color={statusColor(fa.status)}>{fa.status}</Badge></Table.Td>
            <Table.Td>₹{fa.total_paid || '0.00'}</Table.Td>
            <Table.Td>
              {fa.status !== 'waived' && fa.status !== 'paid' && (
                <Button size="xs" color="orange" onClick={() => { setWaiveId(fa.id); setWaiveModal(true); }}>Waive</Button>
              )}
            </Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="New Fee Assignment">
        <Select label="Fee Type" data={(types || []).map((t: any) => ({ value: t.id, label: `${t.name} (₹${t.default_amount})` }))} value={feeTypeId} onChange={(v) => setFeeTypeId(v || '')} mb="sm" />
        <NumberInput label="Amount (₹)" value={amount} onChange={(v) => setAmount(Number(v) || 0)} mb="sm" />
        <TextInput label="Due Date (YYYY-MM-DD)" value={dueDate} onChange={(e) => setDueDate(e.target.value)} mb="sm" />
        <TextInput label="Academic Term" value={term} onChange={(e) => setTerm(e.target.value)} mb="sm" />
        <Textarea label="Student IDs (comma-separated UUIDs)" value={userIds} onChange={(e) => setUserIds(e.target.value)} mb="sm" />
        <Button fullWidth onClick={assignBulk} loading={createMut.isPending}>Assign</Button>
      </Modal>

      <Modal opened={waiveModal} onClose={() => setWaiveModal(false)} title="Waive Fee">
        <TextInput label="Reason" value={waiveReason} onChange={(e) => setWaiveReason(e.target.value)} mb="sm" />
        <Button fullWidth color="orange" onClick={() => waiveMut.mutate({ id: waiveId, reason: waiveReason })} loading={waiveMut.isPending}>Confirm Waive</Button>
      </Modal>
    </>
  );
}
