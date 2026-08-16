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
import { useNavigate } from 'react-router-dom';
import { homeworkApi } from '../../core/api/homework';
import { academicApi } from '../../core/api/academic';
import type {
  HomeworkCreateDTO,
  HomeworkDTO,
  HomeworkUpdateDTO,
} from '../../core/api/dto/homework';
import { normalizeApiError, isForbidden, ApiError } from '../../core/api/errors';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { PermissionDenied } from '../../components/PermissionDenied';
import { useTenant } from '../../core/context/useTenant';
import { usePermissions } from '../../core/access/usePermissions';

type ModalState =
  | { kind: 'create' }
  | { kind: 'edit'; homework: HomeworkDTO }
  | null;

export default function Homeworks() {
  const navigate = useNavigate();
  const { institutionId } = useTenant();
  const { can } = usePermissions();
  const queryClient = useQueryClient();
  const [modal, setModal] = useState<ModalState>(null);
  const [forbidden, setForbidden] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: '',
    description: '',
    subject_id: '',
    section_id: '',
    due_date: '',
    max_score: '',
  });

  const homeworksQuery = useQuery({
    queryKey: ['homeworks', institutionId],
    queryFn: () => homeworkApi.listHomeworks().then((r) => r.data),
    enabled: !!institutionId,
  });

  const subjectsQuery = useQuery({
    queryKey: ['subjects', institutionId],
    queryFn: () => academicApi.listSubjects().then((r) => r.data),
    enabled: !!institutionId,
  });

  const yearsQuery = useQuery({
    queryKey: ['academic-years', institutionId],
    queryFn: () => academicApi.listAcademicYears().then((r) => r.data),
    enabled: !!institutionId,
  });

  const activeYearId = useMemo(() => {
    const years = yearsQuery.data ?? [];
    return (
      years.find((y) => y.status === 'active')?.id ?? years[0]?.id ?? null
    );
  }, [yearsQuery.data]);

  const structureQuery = useQuery({
    queryKey: ['academic-structure', institutionId, activeYearId],
    queryFn: () =>
      academicApi.getStructure(activeYearId ?? '').then((r) => r.data),
    enabled: !!institutionId && !!activeYearId,
  });

  const subjectNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of subjectsQuery.data ?? []) {
      map.set(s.id, s.name);
    }
    return map;
  }, [subjectsQuery.data]);

  const sectionLabels = useMemo(() => {
    const structure = structureQuery.data;
    if (!structure) return new Map<string, string>();
    const gradeNames = new Map(
      structure.grade_levels.map((g) => [g.id, g.name]),
    );
    const classGrade = new Map(
      structure.classes.map((c) => [c.id, c.grade_level_id]),
    );
    const classNames = new Map(structure.classes.map((c) => [c.id, c.name]));
    const map = new Map<string, string>();
    for (const s of structure.sections) {
      const gradeId = classGrade.get(s.class_id);
      const grade = gradeId ? gradeNames.get(gradeId) ?? '' : '';
      const cls = classNames.get(s.class_id) ?? '';
      map.set(s.id, `${grade} ${cls} · ${s.name}`.trim());
    }
    return map;
  }, [structureQuery.data]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['homeworks', institutionId] });

  const createMutation = useMutation({
    mutationFn: (payload: HomeworkCreateDTO) =>
      homeworkApi.createHomework(payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
      resetForm();
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (vars: { id: string; payload: HomeworkUpdateDTO }) =>
      homeworkApi.updateHomework(vars.id, vars.payload).then((r) => r.data),
    onSuccess: () => {
      invalidate();
      setModal(null);
    },
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  const closeMutation = useMutation({
    mutationFn: (hwId: string) => homeworkApi.closeHomework(hwId).then((r) => r.data),
    onSuccess: () => invalidate(),
    onError: (err) => {
      if (isForbidden(err)) setForbidden(normalizeApiError(err).message);
    },
  });

  function resetForm() {
    setForm({
      title: '',
      description: '',
      subject_id: '',
      section_id: '',
      due_date: '',
      max_score: '',
    });
  }

  function openCreate() {
    resetForm();
    setForbidden(null);
    setModal({ kind: 'create' });
  }

  function openEdit(homework: HomeworkDTO) {
    setForm({
      title: homework.title,
      description: homework.description ?? '',
      subject_id: homework.subject_id ?? '',
      section_id: homework.section_id ?? '',
      due_date: homework.due_date,
      max_score: homework.max_score?.toString() ?? '',
    });
    setForbidden(null);
    setModal({ kind: 'edit', homework });
  }

  const columns: DataTableColumn<HomeworkDTO>[] = [
    { key: 'title', header: 'Title', render: (h) => h.title },
    {
      key: 'subject',
      header: 'Subject',
      render: (h) => (h.subject_id ? subjectNames.get(h.subject_id) ?? h.subject_id : '—'),
      hideBelow: 900,
    },
    {
      key: 'section',
      header: 'Section',
      render: (h) => (h.section_id ? sectionLabels.get(h.section_id) ?? h.section_id : '—'),
      hideBelow: 900,
    },
    { key: 'due_date', header: 'Due date', render: (h) => h.due_date, hideBelow: 640 },
    {
      key: 'max_score',
      header: 'Max score',
      render: (h) => (h.max_score?.toString() ?? '—'),
      hideBelow: 640,
    },
    {
      key: 'status',
      header: 'Status',
      render: (h) => <StatusPill status={h.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (h) => (
        <Group gap="xs" wrap="nowrap">
          <Button
            size="xs"
            variant="light"
            onClick={() => navigate(`/homework/${h.id}/submissions`)}
          >
            Submissions
          </Button>
          {can('institution_admin') ? (
            <>
              <Button size="xs" variant="light" onClick={() => openEdit(h)}>
                Edit
              </Button>
              {h.status === 'active' ? (
                <Button
                  size="xs"
                  variant="light"
                  onClick={() => closeMutation.mutate(h.id)}
                >
                  Close
                </Button>
              ) : null}
            </>
          ) : null}
        </Group>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Homeworks"
        subtitle="Assign, edit, and close homework."
        actions={
          can('institution_admin') ? (
            <Button onClick={openCreate}>New homework</Button>
          ) : null
        }
      />

      {forbidden ? <PermissionDenied error={new ApiError(403, forbidden)} /> : null}

      <DataTable
        columns={columns}
        rows={homeworksQuery.data ?? []}
        getRowKey={(h) => h.id}
      />

      <Modal
        opened={modal?.kind === 'create'}
        onClose={() => setModal(null)}
        title="New homework"
      >
        <Stack>
          <TextInput
            label="Title"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.currentTarget.value })}
          />
          <Textarea
            label="Instructions"
            rows={3}
            value={form.description}
            onChange={(e) =>
              setForm({ ...form, description: e.currentTarget.value })
            }
          />
          <Select
            label="Subject"
            searchable
            clearable
            data={(subjectsQuery.data ?? []).map((s) => ({
              value: s.id,
              label: s.name,
            }))}
            value={form.subject_id || null}
            onChange={(v) => setForm({ ...form, subject_id: v ?? '' })}
          />
          <Select
            label="Section"
            searchable
            clearable
            data={(structureQuery.data?.sections ?? []).map((s) => ({
              value: s.id,
              label: sectionLabels.get(s.id) ?? s.name,
            }))}
            value={form.section_id || null}
            onChange={(v) => setForm({ ...form, section_id: v ?? '' })}
          />
          <TextInput
            label="Due date"
            required
            placeholder="YYYY-MM-DD"
            value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.currentTarget.value })}
          />
          <TextInput
            label="Max score"
            inputMode="numeric"
            value={form.max_score}
            onChange={(e) => setForm({ ...form, max_score: e.currentTarget.value })}
          />
          <Button
            loading={createMutation.isPending}
            disabled={!form.title || !form.due_date}
            onClick={() =>
              createMutation.mutate({
                title: form.title,
                description: form.description || null,
                subject_id: form.subject_id || null,
                grade_level_id: null,
                section_id: form.section_id || null,
                due_date: form.due_date,
                max_score: form.max_score ? Number(form.max_score) : null,
              })
            }
          >
            Create
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={modal?.kind === 'edit'}
        onClose={() => setModal(null)}
        title="Edit homework"
      >
        <Stack>
          <TextInput
            label="Title"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.currentTarget.value })}
          />
          <Textarea
            label="Instructions"
            rows={3}
            value={form.description}
            onChange={(e) =>
              setForm({ ...form, description: e.currentTarget.value })
            }
          />
          <TextInput
            label="Due date"
            required
            placeholder="YYYY-MM-DD"
            value={form.due_date}
            onChange={(e) => setForm({ ...form, due_date: e.currentTarget.value })}
          />
          <TextInput
            label="Max score"
            inputMode="numeric"
            value={form.max_score}
            onChange={(e) => setForm({ ...form, max_score: e.currentTarget.value })}
          />
          <Button
            loading={updateMutation.isPending}
            disabled={!form.title || !form.due_date}
            onClick={() => {
              const homework = modal?.kind === 'edit' ? modal.homework : null;
              if (homework) {
                updateMutation.mutate({
                  id: homework.id,
                  payload: {
                    title: form.title,
                    description: form.description || null,
                    due_date: form.due_date,
                    max_score: form.max_score ? Number(form.max_score) : null,
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
