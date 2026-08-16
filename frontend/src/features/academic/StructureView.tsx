import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useQuery } from '@tanstack/react-query';
import { academicApi } from '../../core/api/academic';
import type { SectionDTO } from '../../core/api/dto/academic';
import { PageHeader } from '../../components/PageHeader';
import { StatusPill } from '../../components/StatusPill';
import { useTenant } from '../../core/context/useTenant';
import { TeacherAssignments } from './TeacherAssignments';
import { Enrollments } from './Enrollments';

/**
 * Read-only structure navigation: grade levels → classes → sections.
 * No free-form CRUD for structure nodes (REQ-FE-AC-07); structure changes
 * happen only via academic-year clone/template generation.
 */
export default function StructureView() {
  const { yearId } = useParams<{ yearId: string }>();
  const { institutionId } = useTenant();
  const [selectedSection, setSelectedSection] = useState<SectionDTO | null>(null);

  const structureQuery = useQuery({
    queryKey: ['academic-structure', institutionId, yearId],
    queryFn: () =>
      academicApi.getStructure(yearId ?? '').then((r) => r.data),
    enabled: !!yearId && !!institutionId,
  });

  if (structureQuery.isLoading) {
    return <Loader data-testid="structure-loading" />;
  }

  if (structureQuery.isError) {
    return (
      <Alert color="danger" title="Unable to load structure">
        The academic structure could not be loaded.
      </Alert>
    );
  }

  const structure = structureQuery.data;

  return (
    <>
      <PageHeader
        title="Academic structure"
        subtitle={`Grade levels → classes → sections for ${structure?.academic_year.name ?? '—'}.`}
        actions={
          structure ? (
            <StatusPill status={structure.academic_year.status} />
          ) : null
        }
      />

      <Stack gap="lg">
        {(structure?.grade_levels ?? []).map((grade) => {
          const gradeClasses = (structure?.classes ?? []).filter(
            (c) => c.grade_level_id === grade.id,
          );
          return (
            <Card key={grade.id} withBorder padding="md">
              <Title order={4}>{grade.name}</Title>
              <Stack gap="xs" mt="sm">
                {gradeClasses.map((cls) => {
                  const classSections = (structure?.sections ?? []).filter(
                    (s) => s.class_id === cls.id,
                  );
                  return (
                    <Card key={cls.id} withBorder padding="xs">
                      <Group justify="space-between">
                        <Text fw={600}>{cls.name}</Text>
                        <Badge variant="light" color="blue">
                          {classSections.length} section
                          {classSections.length === 1 ? '' : 's'}
                        </Badge>
                      </Group>
                      <Group gap="xs" mt="xs">
                        {classSections.map((section) => (
                          <Button
                            key={section.id}
                            size="xs"
                            variant={selectedSection?.id === section.id ? 'filled' : 'light'}
                            onClick={() => setSelectedSection(section)}
                          >
                            {section.name}
                          </Button>
                        ))}
                        {classSections.length === 0 ? (
                          <Text size="sm" c="dimmed">
                            No sections
                          </Text>
                        ) : null}
                      </Group>
                    </Card>
                  );
                })}
              </Stack>
            </Card>
          );
        })}
      </Stack>

      {selectedSection ? (
        <Stack mt="xl" gap="xl">
          <Title order={3}>Section {selectedSection.name}</Title>
          <TeacherAssignments
            sectionId={selectedSection.id}
            academicYearId={selectedSection.academic_year_id}
          />
          <Enrollments sectionId={selectedSection.id} />
        </Stack>
      ) : (
        <Text c="dimmed" size="sm" mt="xl">
          Select a section to manage its teacher assignments and enrollments.
        </Text>
      )}
    </>
  );
}
