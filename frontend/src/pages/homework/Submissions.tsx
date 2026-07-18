import { useState } from 'react';
import { Table, Button, Modal, Textarea, NumberInput, Group, Loader, Badge, Text } from '@mantine/core';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { notifications } from '@mantine/notifications';
import api from '../../api/client';

export default function Submissions() {
  const { id: hwId } = useParams();
  const qc = useQueryClient();
  const [submitOpen, setSubmitOpen] = useState(false);
  const [content, setContent] = useState('');
  const [gradeOpen, setGradeOpen] = useState(false);
  const [gradeSubId, setGradeSubId] = useState('');
  const [score, setScore] = useState<number>(0);
  const [feedback, setFeedback] = useState('');

  const { data: hw } = useQuery({ queryKey: ['homework', hwId], queryFn: () => api.get(`/v1/homeworks/${hwId}`).then(r => r.data), enabled: !!hwId });
  const { data: subs, isLoading } = useQuery({ queryKey: ['submissions', hwId], queryFn: () => api.get(`/v1/submissions?homework_id=${hwId}`).then(r => r.data), enabled: !!hwId });

  const submitMut = useMutation({ mutationFn: (d: any) => api.post('/v1/submissions', d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['submissions', hwId] }); setSubmitOpen(false); notifications.show({ message: 'Submitted!', color: 'green' }); } });
  const gradeMut = useMutation({ mutationFn: ({ id, d }: any) => api.post(`/v1/submissions/${id}/grade`, d), onSuccess: () => { qc.invalidateQueries({ queryKey: ['submissions', hwId] }); setGradeOpen(false); notifications.show({ message: 'Graded!', color: 'green' }); } });

  const statusColor = (s: string) => s === 'submitted' ? 'blue' : s === 'late' ? 'red' : s === 'graded' ? 'green' : 'gray';

  if (isLoading) return <Loader />;
  return (
    <>
      <Text size="lg" fw={700} mb="md">{hw?.title} — {hw?.subject} ({hw?.grade_level} {hw?.section})</Text>
      <Text size="sm" mb="md">Due: {hw?.due_date} | Max Score: {hw?.max_score} | Status: <Badge color={statusColor(hw?.status || '')}>{hw?.status}</Badge></Text>
      <Group mb="md">
        {hw?.status === 'active' && <Button onClick={() => setSubmitOpen(true)}>+ Submit (as Student)</Button>}
      </Group>
      <Table striped>
        <Table.Thead><Table.Tr><Table.Th>Student</Table.Th><Table.Th>Content</Table.Th><Table.Th>Status</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{(subs || []).map((s: any) => (
          <Table.Tr key={s.id}>
            <Table.Td>{s.student_id?.slice(0, 8)}</Table.Td>
            <Table.Td>{s.content?.slice(0, 50)}{s.content?.length > 50 ? '...' : ''}</Table.Td>
            <Table.Td><Badge color={statusColor(s.status)}>{s.status}</Badge></Table.Td>
            <Table.Td>{s.submitted_at?.slice(0, 10)}</Table.Td>
            <Table.Td>
              {s.status !== 'graded' && <Button size="xs" onClick={() => { setGradeSubId(s.id); setGradeOpen(true); }}>Grade</Button>}
            </Table.Td>
          </Table.Tr>
        ))}</Table.Tbody>
      </Table>

      <Modal opened={submitOpen} onClose={() => setSubmitOpen(false)} title="Submit Homework">
        <Textarea label="Your Answer" value={content} onChange={(e) => setContent(e.target.value)} mb="sm" minRows={4} />
        <Button fullWidth onClick={() => submitMut.mutate({ homework_id: hwId, content })} loading={submitMut.isPending}>Submit</Button>
      </Modal>

      <Modal opened={gradeOpen} onClose={() => setGradeOpen(false)} title="Grade Submission">
        <NumberInput label="Score" value={score} onChange={(v) => setScore(Number(v) || 0)} mb="sm" />
        <Textarea label="Feedback" value={feedback} onChange={(e) => setFeedback(e.target.value)} mb="sm" />
        <Button fullWidth onClick={() => gradeMut.mutate({ id: gradeSubId, d: { score, feedback } })} loading={gradeMut.isPending}>Submit Grade</Button>
      </Modal>
    </>
  );
}
