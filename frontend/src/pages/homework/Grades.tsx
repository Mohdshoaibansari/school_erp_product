import { Table, Badge, Loader } from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';

export default function Grades() {
  const { data: grades, isLoading } = useQuery({ queryKey: ['grades'], queryFn: () => api.get('/v1/grades').then(r => r.data) });

  if (isLoading) return <Loader />;
  return (
    <Table striped>
      <Table.Thead><Table.Tr><Table.Th>Submission</Table.Th><Table.Th>Score</Table.Th><Table.Th>Max</Table.Th><Table.Th>Feedback</Table.Th><Table.Th>Graded At</Table.Th></Table.Tr></Table.Thead>
      <Table.Tbody>{(grades || []).map((g: any) => (
        <Table.Tr key={g.id}>
          <Table.Td>{g.submission_id?.slice(0, 8)}</Table.Td>
          <Table.Td><Badge size="lg" color={g.score >= (g.max_score || 100) * 0.7 ? 'green' : g.score > 0 ? 'yellow' : 'red'}>{g.score}</Badge></Table.Td>
          <Table.Td>{g.max_score}</Table.Td>
          <Table.Td>{g.feedback}</Table.Td>
          <Table.Td>{g.graded_at?.slice(0, 10)}</Table.Td>
        </Table.Tr>
      ))}</Table.Tbody>
    </Table>
  );
}
