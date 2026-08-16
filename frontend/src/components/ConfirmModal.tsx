import { Button, Group, Modal, Text } from '@mantine/core';

export function ConfirmModal({
  opened,
  title,
  message,
  confirmLabel = 'Confirm',
  loading = false,
  onConfirm,
  onClose,
}: {
  opened: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  loading?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal opened={opened} onClose={onClose} title={title} centered>
      <Text size="sm" mb="lg">
        {message}
      </Text>
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Cancel
        </Button>
        <Button color="danger" loading={loading} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </Group>
    </Modal>
  );
}
