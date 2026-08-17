import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { academicApi } from '../../core/api/academic';
import { usersApi } from '../../core/api/users';
import type {
  TeacherAssignmentCreateDTO,
  TeacherAssignmentDTO,
} from '../../core/api/dto/academic';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';

export function TeacherAssignments({
  sectionId,
  academicYearId,
}: {
  sectionId: string;
  academicYearId: string;
}) {
  const { institutionId } = useTenant();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [teacherId, setTeacherId] = useState<string | null>(null);
  const [subjectId, setSubjectId] = useState<string | null>(null);

  const assignmentsQuery = useQuery({
    queryKey: ['teacher-assignments', institutionId, sectionId],
    queryFn: () =>
      academicApi
        .listTeacherAssignments({ section_id: sectionId })
        .then((r) => r.data),
    enabled: !!sectionId && !!institutionId,
  });

  const subjectsQuery = useQuery({
    queryKey: ['subjects', institutionId, academicYearId],
    queryFn: () =>
      academicApi.listSubjects(academicYearId).then((r) => r.data),
    enabled: !!institutionId && !!academicYearId,
  });

  const usersQuery = useQuery({
    queryKey: ['users', institutionId],
    queryFn: () => usersApi.listUsers().then((r) => r.data),
    enabled: !!institutionId,
  });

  const userNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersQuery.data ?? []) {
      map.set(u.id, u.name);
    }
    return map;
  }, [usersQuery.data]);

  const subjectNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of subjectsQuery.data ?? []) {
      map.set(s.id, s.name);
    }
    return map;
  }, [subjectsQuery.data]);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['teacher-assignments', institutionId, sectionId],
    });

  const createMutation = useMutation({
    mutationFn: (payload: TeacherAssignmentCreateDTO) =>
      academicApi.createTeacherAssignment(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setOpen(false);
      setTeacherId(null);
      setSubjectId(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (assignmentId: string) =>
      academicApi.removeTeacherAssignment(assignmentId),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<TeacherAssignmentDTO>[] = [
    {
      key: 'teacher',
      header: 'Teacher',
      render: (a) => userNames.get(a.teacher_id) ?? a.teacher_id,
    },
    {
      key: 'subject',
      header: 'Subject',
      render: (a) => subjectNames.get(a.subject_id) ?? a.subject_id,
    },
    {
      key: 'status',
      header: 'Status',
      render: (a) => <StatusPill status={a.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (a) => (
        <Button
          size="xs"
          variant="light"
          color="danger"
          onClick={() => removeMutation.mutate(a.id)}
        >
          Remove
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Teacher assignments</Title>
        <Button
          size="xs"
          onClick={() => {
            setForbidden(null);
            setOpen(true);
          }}
        >
          Assign teacher
        </Button>
      </Group>

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={assignmentsQuery.data ?? []}
        getRowKey={(a) => a.id}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title="Assign teacher to subject">
        <Stack>
          <Select
            label="Teacher"
            searchable
            data={(usersQuery.data ?? []).map((u) => ({
              value: u.id,
              label: `${u.name} (${u.email})`,
            }))}
            value={teacherId}
            onChange={(value) => setTeacherId(value ?? '')}
          />
          <Select
            label="Subject"
            searchable
            data={(subjectsQuery.data ?? []).map((s) => ({
              value: s.id,
              label: s.name,
            }))}
            value={subjectId}
            onChange={(value) => setSubjectId(value ?? '')}
          />
          <Alert color="blue" variant="light">
            <Text size="sm">
              The teacher will be assigned to teach this subject in the selected section.
            </Text>
          </Alert>
          <Button
            loading={createMutation.isPending}
            disabled={!teacherId || !subjectId}
            onClick={() => {
              if (teacherId && subjectId) {
                createMutation.mutate({
                  teacher_id: teacherId,
                  section_id: sectionId,
                  subject_id: subjectId,
                });
              }
            }}
          >
            Assign
          </Button>
        </Stack>
      </Modal>
    </div>
  );
}
