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
  StudentEnrollmentCreateDTO,
  StudentEnrollmentDTO,
} from '../../core/api/dto/academic';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';

export function Enrollments({
  sectionId,
}: {
  sectionId: string;
}) {
  const { institutionId } = useTenant();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [studentId, setStudentId] = useState<string | null>(null);

  const enrollmentsQuery = useQuery({
    queryKey: ['enrollments', institutionId, sectionId],
    queryFn: () =>
      academicApi.listEnrollments(sectionId).then((r) => r.data),
    enabled: !!sectionId && !!institutionId,
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

  const enrolledStudentIds = useMemo(() => {
    return new Set(
      (enrollmentsQuery.data ?? []).map((e) => e.student_id),
    );
  }, [enrollmentsQuery.data]);

  const rosterOptions = useMemo(() => {
    return (usersQuery.data ?? [])
      .filter((u) => !enrolledStudentIds.has(u.id))
      .map((u) => ({ value: u.id, label: `${u.name} (${u.email})` }));
  }, [usersQuery.data, enrolledStudentIds]);

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['enrollments', institutionId, sectionId],
    });

  const enrollMutation = useMutation({
    mutationFn: (payload: StudentEnrollmentCreateDTO) =>
      academicApi.enrollStudent(sectionId, payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setOpen(false);
      setStudentId(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (enrollmentId: string) =>
      academicApi.removeEnrollment(enrollmentId),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<StudentEnrollmentDTO>[] = [
    {
      key: 'student',
      header: 'Student',
      render: (e) => userNames.get(e.student_id) ?? e.student_id,
    },
    {
      key: 'status',
      header: 'Status',
      render: (e) => <StatusPill status={e.status} />,
    },
    {
      key: 'enrolled_at',
      header: 'Enrolled',
      render: (e) => e.enrolled_at.slice(0, 10),
      hideBelow: 640,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (e) => (
        <Button
          size="xs"
          variant="light"
          color="danger"
          onClick={() => removeMutation.mutate(e.id)}
        >
          Remove
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Group justify="space-between" mb="sm">
        <Title order={4}>Enrollments</Title>
        <Button
          size="xs"
          onClick={() => {
            setForbidden(null);
            setOpen(true);
          }}
        >
          Enroll student
        </Button>
      </Group>

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={enrollmentsQuery.data ?? []}
        getRowKey={(e) => e.id}
      />

      <Modal opened={open} onClose={() => setOpen(false)} title="Enroll student">
        <Stack>
          <Select
            label="Student"
            searchable
            data={rosterOptions}
            value={studentId}
            onChange={setStudentId}
          />
          <Alert color="blue" variant="light">
            <Text size="sm">
              Select a student from the roster to enroll into this section.
            </Text>
          </Alert>
          <Button
            loading={enrollMutation.isPending}
            disabled={!studentId}
            onClick={() => {
              if (studentId) {
                enrollMutation.mutate({
                  student_id: studentId,
                  section_id: sectionId,
                });
              }
            }}
          >
            Enroll
          </Button>
        </Stack>
      </Modal>
    </div>
  );
}
