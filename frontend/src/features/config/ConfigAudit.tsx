import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { configApi } from '../../core/api/config';
import type { ConfigAuditDTO } from '../../core/api/dto/config';
import { DataTable, type DataTableColumn } from '../../components/DataTable';
import { PageHeader } from '../../components/PageHeader';
import { useTenant } from '../../core/context/useTenant';

export function ConfigAudit() {
  const { institutionId } = useTenant();

  const auditQuery = useQuery({
    queryKey: ['config-audit', institutionId],
    queryFn: () =>
      configApi.listAudit({ page_size: 200 }).then((r) => r.data.items),
    enabled: !!institutionId,
  });

  const keysQuery = useQuery({
    queryKey: ['config-keys', institutionId],
    queryFn: () =>
      configApi
        .listKeys({ include_deprecated: true, page_size: 200 })
        .then((r) => r.data.items),
    enabled: !!institutionId,
  });

  const keyNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const k of keysQuery.data ?? []) {
      map.set(k.id, k.key);
    }
    return map;
  }, [keysQuery.data]);

  const columns: DataTableColumn<ConfigAuditDTO>[] = [
    {
      key: 'key',
      header: 'Key',
      render: (a) => keyNames.get(a.key_id) ?? a.key_id,
    },
    { key: 'action', header: 'Action', render: (a) => a.action },
    {
      key: 'actor_role',
      header: 'Actor role',
      render: (a) => a.actor_role,
      hideBelow: 900,
    },
    {
      key: 'timestamp',
      header: 'When',
      render: (a) => new Date(a.timestamp).toLocaleString(),
    },
  ];

  return (
    <>
      <PageHeader
        title="Configuration audit"
        subtitle="Who changed which configuration value and when."
      />
      <DataTable
        columns={columns}
        rows={auditQuery.data ?? []}
        getRowKey={(a) => a.id}
      />
    </>
  );
}
