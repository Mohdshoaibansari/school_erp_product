import { useMemo, useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  TextInput,
  Textarea,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { homeworkApi } from '../../core/api/homework';
import { usersApi } from '../../core/api/users';
import type { GradeDTO, GradeUpdateDTO } from '../../core/api/dto/homework';
import type { SubmissionDTO } from '../../core/api/dto/homework';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

interface GradeRow {
  grade: GradeDTO;
  studentName: string;
  homeworkTitle: string;
}

export function Grades() {
  const { institutionId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<GradeDTO | null>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [score, setScore] = useState('');
  const [feedback, setFeedback] = useState('');
  const [homeworkFilter, setHomeworkFilter] = useState<string | null>(null);
  const [studentFilter, setStudentFilter] = useState<string | null>(null);

  const gradesQuery = useQuery({
    queryKey: ['grades', institutionId],
    queryFn: () => homeworkApi.listGrades().then((r) => r.data),
    enabled: !!institutionId,
  });

  const submissionsQuery = useQuery({
    queryKey: ['submissions', institutionId],
    queryFn: () => homeworkApi.listSubmissions().then((r) => r.data),
    enabled: !!institutionId,
  });

  const homeworksQuery = useQuery({
    queryKey: ['homeworks', institutionId],
    queryFn: () => homeworkApi.listHomeworks().then((r) => r.data),
    enabled: !!institutionId,
  });

  const usersQuery = useQuery({
    queryKey: ['users', institutionId],
    queryFn: () => usersApi.listUsers().then((r) => r.data),
    enabled: !!institutionId,
  });

  const submissionById = useMemo(() => {
    const map = new Map<string, SubmissionDTO>();
    for (const s of submissionsQuery.data ?? []) {
      map.set(s.id, s);
    }
    return map;
  }, [submissionsQuery.data]);

  const homeworkTitles = useMemo(() => {
    const map = new Map<string, string>();
    for (const h of homeworksQuery.data ?? []) {
      map.set(h.id, h.title);
    }
    return map;
  }, [homeworksQuery.data]);

  const studentNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersQuery.data ?? []) {
      map.set(u.id, u.name);
    }
    return map;
  }, [usersQuery.data]);

  const rows = useMemo<GradeRow[]>(() => {
    return (gradesQuery.data ?? []).map((grade) => {
      const submission = submissionById.get(grade.submission_id);
      const studentName = submission
        ? studentNames.get(submission.student_id) ??
          submission.student_name ??
          submission.student_id
        : '—';
      const homeworkTitle = submission
        ? homeworkTitles.get(submission.homework_id) ?? submission.homework_id
        : '—';
      return { grade, studentName, homeworkTitle };
    });
  }, [gradesQuery.data, submissionById, studentNames, homeworkTitles]);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const submission = submissionById.get(row.grade.submission_id);
      if (homeworkFilter && submission?.homework_id !== homeworkFilter) return false;
      if (studentFilter && submission?.student_id !== studentFilter) return false;
      return true;
    });
  }, [rows, submissionById, homeworkFilter, studentFilter]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['grades', institutionId] });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; payload: GradeUpdateDTO }) =>
      homeworkApi.updateGrade(vars.id, vars.payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setEditing(null);
      setScore('');
      setFeedback('');
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function openEdit(grade: GradeDTO) {
    setScore(grade.score.toString());
    setFeedback(grade.feedback ?? '');
    setForbidden(null);
    setEditing(grade);
  }

  const columns: DataTableColumn<GradeRow>[] = [
    { key: 'student', header: 'Student', render: (r) => r.studentName },
    { key: 'homework', header: 'Homework', render: (r) => r.homeworkTitle },
    {
      key: 'score',
      header: 'Score',
      render: (r) =>
        r.grade.max_score != null
          ? `${r.grade.score} / ${r.grade.max_score}`
          : String(r.grade.score),
    },
    {
      key: 'feedback',
      header: 'Feedback',
      render: (r) => r.grade.feedback ?? '—',
      hideBelow: 900,
    },
    {
      key: 'graded_at',
      header: 'Graded',
      render: (r) => r.grade.graded_at.slice(0, 10),
      hideBelow: 640,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (r) =>
        can('institution_admin') ? (
          <Button size="xs" variant="light" onClick={() => openEdit(r.grade)}>
            Edit
          </Button>
        ) : null,
    },
  ];

  return (
    <>
      <PageHeader
        title="Grades"
        subtitle="View and update grades per homework and per student."
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <Group mb="md">
        <Select
          placeholder="Filter by homework"
          searchable
          clearable
          data={(homeworksQuery.data ?? []).map((h) => ({
            value: h.id,
            label: h.title,
          }))}
          value={homeworkFilter}
          onChange={setHomeworkFilter}
        />
        <Select
          placeholder="Filter by student"
          searchable
          clearable
          data={(usersQuery.data ?? []).map((u) => ({
            value: u.id,
            label: `${u.name} (${u.email})`,
          }))}
          value={studentFilter}
          onChange={setStudentFilter}
        />
      </Group>

      <DataTable
        columns={columns}
        rows={filteredRows}
        getRowKey={(r) => r.grade.id}
      />

      <Modal opened={!!editing} onClose={() => setEditing(null)} title="Edit grade">
        <Stack>
          <TextInput
            label="Score"
            required
            inputMode="numeric"
            value={score}
            onChange={(e) => setScore(e.currentTarget.value)}
          />
          <Textarea
            label="Feedback"
            rows={3}
            value={feedback}
            onChange={(e) => setFeedback(e.currentTarget.value)}
          />
          <Button
            loading={updateMutation.isPending}
            disabled={!score}
            onClick={() => {
              if (editing) {
                updateMutation.mutate({
                  id: editing.id,
                  payload: {
                    score: Number(score),
                    feedback: feedback || null,
                  },
                });
              }
            }}
          >
            Save
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
