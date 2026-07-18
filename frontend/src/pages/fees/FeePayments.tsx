import { useState } from 'react';
import { Table, Button, Modal, NumberInput, Group, Loader, Select } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function FeePayments() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [faId, setFaId] = useState('');
  const [amount, setAmount] = useState<number>(0);
  const [method, setMethod] = useState('Cash');

  const { data: assignments } = useQuery({ queryKey: ['fee-assignments'], queryFn: () => api.get('/v1/fee-assignments').then(r => r.data) });
  const { data: payments, isLoading } = useQuery({ queryKey: ['payments'], queryFn: () => api.get('/v1/payments').then(r => r.data) });
  const createMut = useMutation({ mutationFn: (d: any) => api.post('/v1/payments', d), onSuccess: (res) => { qc.invalidateQueries({ queryKey: ['payments'] }); qc.invalidateQueries({ queryKey: ['fee-assignments'] }); setModalOpen(false); notifications.show({ message: `Paid — Receipt: ${res.data.receipt_number}`, color: 'green' }); } });

  if (isLoading) return <Loader />;
  return (
    <>
      <Group mb="md"><Button onClick={() => setModalOpen(true)}>+ Record Payment</Button></Group>
      <Table striped>
        <Table.Thead><Table.Tr><Table.Th>Receipt</Table.Th><Table.Th>Assignment</Table.Th><Table.Th>Amount</Table.Th><Table.Th>Method</Table.Th><Table.Th>Date</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{(payments || []).map((p: any) => (
          <Table.Tr key={p.id}>
            <Table.Td>{p.receipt_number || p.id?.slice(0, 8)}</Table.Td>
            <Table.Td>{p.fee_assignment_id?.slice(0, 8)}</Table.Td>
            <Table.Td>₹{p.amount}</Table.Td>
            <Table.Td>{p.payment_method}</Table.Td>
            <Table.Td>{p.payment_date}</Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Record Payment">
        <Select label="Fee Assignment" data={(assignments || []).filter((a: any) => a.status !== 'paid' && a.status !== 'waived').map((a: any) => ({ value: a.id, label: `₹${a.amount} (${a.status})` }))} value={faId} onChange={(v) => setFaId(v || '')} mb="sm" />
        <NumberInput label="Amount (₹)" value={amount} onChange={(v) => setAmount(Number(v) || 0)} mb="sm" />
        <Select label="Method" data={['Cash', 'Card', 'Online', 'Cheque', 'Bank Transfer']} value={method} onChange={(v) => setMethod(v || 'Cash')} mb="sm" />
        <Button fullWidth onClick={() => createMut.mutate({ fee_assignment_id: faId, amount, payment_method: method })} loading={createMut.isPending}>Record</Button>
      </Modal>
    </>
  );
}
