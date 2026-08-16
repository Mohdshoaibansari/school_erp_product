import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { homeworkApi } from '../../core/api/homework';
import type { GradeCreateDTO, SubmissionDTO } from '../../core/api/dto/homework';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

type ModalState =
  | { kind: 'view'; submission: SubmissionDTO }
  | { kind: 'grade'; submission: SubmissionDTO }
  | null;

export default function Submissions() {
  const { hwId } = useParams<{ hwId: string }>();
  const { institutionId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [score, setScore] = useState('');
  const [feedback, setFeedback] = useState('');

  const homeworkQuery = useQuery({
    queryKey: ['homework', institutionId, hwId],
    queryFn: () => homeworkApi.getHomework(hwId ?? '').then((r) => r.data),
    enabled: !!institutionId && !!hwId,
  });

  const submissionsQuery = useQuery({
    queryKey: ['submissions', institutionId, hwId],
    queryFn: () =>
      homeworkApi.listSubmissions({ homework_id: hwId }).then((r) => r.data),
    enabled: !!institutionId && !!hwId,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['submissions', institutionId, hwId] });

  const gradeMutation = useMutation({
    mutationFn: (vars: { submissionId: string; payload: GradeCreateDTO }) =>
      homeworkApi.gradeSubmission(vars.submissionId, vars.payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
      setScore('');
      setFeedback('');
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const columns: DataTableColumn<SubmissionDTO>[] = [
    {
      key: 'student',
      header: 'Student',
      render: (s) => s.student_name ?? s.student_id,
    },
    {
      key: 'status',
      header: 'Status',
      render: (s) => <StatusPill status={s.status} />,
    },
    {
      key: 'submitted_at',
      header: 'Submitted',
      render: (s) => s.submitted_at.slice(0, 10),
      hideBelow: 640,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (s) => (
        <Group gap="xs" wrap="nowrap">
          <Button size="xs" variant="light" onClick={() => setModal({ kind: 'view', submission: s })}>
            View
          </Button>
          {can('institution_admin') && s.status !== 'graded' ? (
            <Button
              size="xs"
              variant="light"
              onClick={() => {
                setScore('');
                setFeedback('');
                setForbidden(null);
                setModal({ kind: 'grade', submission: s });
              }}
            >
              Grade
            </Button>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Submissions"
        subtitle={`Submissions for ${homeworkQuery.data?.title ?? 'homework'}.`}
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={submissionsQuery.data ?? []}
        getRowKey={(s) => s.id}
      />

      <Modal
        opened={modal?.kind === 'view'}
        onClose={() => setModal(null)}
        title="Submission"
      >
        <Stack>
          <Text size="sm" fw={600}>
            {modal?.kind === 'view' ? modal.submission.student_name ?? modal.submission.student_id : ''}
          </Text>
          <Text size="sm" c="dimmed">
            {modal?.kind === 'view' ? modal.submission.content ?? 'No content submitted.' : ''}
          </Text>
          <Button variant="default" onClick={() => setModal(null)}>
            Close
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'grade'}
        onClose={() => setModal(null)}
        title="Grade submission"
      >
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
            loading={gradeMutation.isPending}
            disabled={!score}
            onClick={() => {
              const submission = modal?.kind === 'grade' ? modal.submission : null;
              if (submission) {
                gradeMutation.mutate({
                  submissionId: submission.id,
                  payload: {
                    score: Number(score),
                    feedback: feedback || null,
                  },
                });
              }
            }}
          >
            Grade
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
