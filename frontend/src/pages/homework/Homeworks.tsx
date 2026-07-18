import { useState } from 'react';
import { Table, Button, Modal, TextInput, NumberInput, Textarea, Group, Loader, Badge } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';
import { useNavigate } from 'react-router-dom';

export default function Homeworks() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [subject, setSubject] = useState('');
  const [grade, setGrade] = useState('');
  const [section, setSection] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [maxScore, setMaxScore] = useState<number>(100);

  const { data: homeworks, isLoading } = useQuery({ queryKey: ['homeworks'], queryFn: () => api.get('/v1/homeworks').then(r => r.data) });
  const createMut = useMutation({ mutationFn: (d: any) => api.post('/v1/homeworks', d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['homeworks'] }); setModalOpen(false); notifications.show({ message: 'Created', color: 'green' }); } });
  const updateMut = useMutation({ mutationFn: ({ id, d }: any) => api.patch(`/v1/homeworks/${id}`, d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['homeworks'] }); setModalOpen(false); } });
  const closeMut = useMutation({ mutationFn: (id: string) => api.post(`/v1/homeworks/${id}/close`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['homeworks'] }); notifications.show({ message: 'Closed', color: 'orange' }); } });
  const deleteMut = useMutation({ mutationFn: (id: string) => api.delete(`/v1/homeworks/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ['homeworks'] }); } });

  const openCreate = () => { setEditId(null); setTitle(''); setDesc(''); setSubject(''); setGrade(''); setSection(''); setDueDate(''); setMaxScore(100); setModalOpen(true); };
  const openEdit = (hw: any) => { setEditId(hw.id); setTitle(hw.title); setDesc(hw.description || ''); setSubject(hw.subject || ''); setGrade(hw.grade_level || ''); setSection(hw.section || ''); setDueDate(hw.due_date); setMaxScore(hw.max_score || 100); setModalOpen(true); };
  const save = () => {
    const d: any = { title, description: desc, subject, grade_level: grade, section, due_date: dueDate, max_score: maxScore };
    if (editId) { updateMut.mutate({ id: editId, d }); } else { createMut.mutate(d); }
  };

  const statusColor = (s: string) => s === 'active' ? 'green' : s === 'closed' ? 'orange' : 'gray';

  if (isLoading) return <Loader />;
  return (
    <>
      <Group mb="md"><Button onClick={openCreate}>+ New Homework</Button></Group>
      <Table striped>
        <Table.Thead><Table.Tr><Table.Th>Title</Table.Th><Table.Th>Subject</Table.Th><Table.Th>Grade</Table.Th><Table.Th>Due</Table.Th><Table.Th>Status</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{(homeworks || []).map((hw: any) => (
          <Table.Tr key={hw.id}>
            <Table.Td>{hw.title}</Table.Td>
            <Table.Td>{hw.subject}</Table.Td>
            <Table.Td>{hw.grade_level} {hw.section}</Table.Td>
            <Table.Td>{hw.due_date}</Table.Td>
            <Table.Td><Badge color={statusColor(hw.status)}>{hw.status}</Badge></Table.Td>
            <Table.Td>
              <Group gap="xs">
                {hw.status === 'active' && <Button size="xs" onClick={() => closeMut.mutate(hw.id)}>Close</Button>}
                <Button size="xs" variant="outline" onClick={() => openEdit(hw)}>Edit</Button>
                <Button size="xs" variant="outline" onClick={() => navigate(`/homework/${hw.id}/submissions`)}>Submissions</Button>
                <Button size="xs" color="red" onClick={() => deleteMut.mutate(hw.id)}>Archive</Button>
              </Group>
            </Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editId ? 'Edit Homework' : 'New Homework'} size="lg">
        <TextInput label="Title" value={title} onChange={(e) => setTitle(e.target.value)} mb="sm" />
        <Textarea label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} mb="sm" />
        <TextInput label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} mb="sm" />
        <TextInput label="Grade Level" value={grade} onChange={(e) => setGrade(e.target.value)} mb="sm" />
        <TextInput label="Section" value={section} onChange={(e) => setSection(e.target.value)} mb="sm" />
        <TextInput label="Due Date (YYYY-MM-DD)" value={dueDate} onChange={(e) => setDueDate(e.target.value)} mb="sm" />
        <NumberInput label="Max Score" value={maxScore} onChange={(v) => setMaxScore(Number(v) || 0)} mb="sm" />
        <Button fullWidth onClick={save} loading={createMut.isPending || updateMut.isPending}>Save</Button>
      </Modal>
    </>
  );
}
