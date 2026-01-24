import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { downloadAuditLogs, fetchAuditLogs, type AuditLogEntry } from '../../services/auditLogs';
import { downloadSystemLog, fetchSystemLogs, type SystemLogItem } from '../../services/system';
import { useToast } from '../../context/ToastContext';
import { Card } from '../common/Card';
import { formatDateTime, type DateTimePreferences } from '../../utils/dateTime';

interface LoggingPanelProps {
  timeZone?: string | null;
  dateFormat?: DateTimePreferences['dateFormat'];
  timeFormat?: DateTimePreferences['timeFormat'];
  locale?: string | null;
}

export const LoggingPanel: React.FC<LoggingPanelProps> = ({
  timeZone,
  dateFormat = 'locale',
  timeFormat = 'locale',
  locale = null,
}) => {
  const { showError, showSuccess } = useToast();
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditAction, setAuditAction] = useState('');
  const [auditTargetType, setAuditTargetType] = useState('');
  const [auditQuery, setAuditQuery] = useState('');
  const [auditSince, setAuditSince] = useState('');
  const [auditUntil, setAuditUntil] = useState('');
  const [auditOffset, setAuditOffset] = useState(0);
  const [isExporting, setIsExporting] = useState(false);

  const [systemLogs, setSystemLogs] = useState<SystemLogItem[]>([]);
  const [systemLoading, setSystemLoading] = useState(true);

  const auditLimit = 50;
  const auditPage = Math.floor(auditOffset / auditLimit) + 1;
  const auditPageCount = Math.max(1, Math.ceil(auditTotal / auditLimit));

  const auditFilters = useMemo(
    () => ({
      action: auditAction.trim() || undefined,
      target_type: auditTargetType.trim() || undefined,
      q: auditQuery.trim() || undefined,
      since: auditSince || undefined,
      until: auditUntil || undefined,
      limit: auditLimit,
      offset: auditOffset,
    }),
    [auditAction, auditTargetType, auditQuery, auditSince, auditUntil, auditOffset]
  );

  const loadAuditLogs = useCallback(async () => {
    setAuditLoading(true);
    try {
      const response = await fetchAuditLogs(auditFilters);
      setAuditLogs(response.items);
      setAuditTotal(response.total);
    } catch (error) {
      showError('Failed to load audit logs.');
    } finally {
      setAuditLoading(false);
    }
  }, [auditFilters, showError]);

  const loadSystemLogs = useCallback(async () => {
    setSystemLoading(true);
    try {
      const response = await fetchSystemLogs();
      setSystemLogs(response);
    } catch (error) {
      showError('Failed to load system logs.');
    } finally {
      setSystemLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    loadAuditLogs();
  }, [loadAuditLogs]);

  useEffect(() => {
    loadSystemLogs();
  }, [loadSystemLogs]);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await downloadAuditLogs({
        ...auditFilters,
        limit: undefined,
        offset: undefined,
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'audit_logs.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showSuccess('Audit logs exported.');
    } catch (error) {
      showError('Failed to export audit logs.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadSystemLog = async (logName: string) => {
    try {
      const blob = await downloadSystemLog(logName);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = logName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showSuccess('Log download started.');
    } catch (error) {
      showError('Failed to download log.');
    }
  };

  const handleAuditPageChange = (nextPage: number) => {
    const clamped = Math.max(1, Math.min(nextPage, auditPageCount));
    setAuditOffset((clamped - 1) * auditLimit);
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-lg font-medium text-pine-deep">Audit Logs</h2>
            <p className="text-sm text-pine-mid">
              Review admin and authentication events. Filter by action, target, or keyword.
            </p>
          </div>
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className="px-4 py-2 bg-forest-green text-white rounded-lg hover:bg-pine-deep transition disabled:opacity-50"
          >
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <input
            type="text"
            value={auditAction}
            onChange={(e) => {
              setAuditOffset(0);
              setAuditAction(e.target.value);
            }}
            placeholder="Filter by action"
            className="min-w-0 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
          />
          <input
            type="text"
            value={auditTargetType}
            onChange={(e) => {
              setAuditOffset(0);
              setAuditTargetType(e.target.value);
            }}
            placeholder="Target type"
            className="min-w-0 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
          />
          <input
            type="text"
            value={auditQuery}
            onChange={(e) => {
              setAuditOffset(0);
              setAuditQuery(e.target.value);
            }}
            placeholder="Search keyword"
            className="min-w-0 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
          />
          <div className="flex flex-col gap-1 md:col-span-2 min-w-0">
            <span className="text-xs text-pine-mid">Date range</span>
            <div className="flex flex-col gap-2">
              <input
                type="datetime-local"
                value={auditSince}
                onChange={(e) => {
                  setAuditOffset(0);
                  setAuditSince(e.target.value);
                }}
                placeholder="From"
                aria-label="Audit log start date"
                className="w-full min-w-0 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              />
              <input
                type="datetime-local"
                value={auditUntil}
                onChange={(e) => {
                  setAuditOffset(0);
                  setAuditUntil(e.target.value);
                }}
                placeholder="To"
                aria-label="Audit log end date"
                className="w-full min-w-0 px-3 py-2 border border-sage-mid rounded-lg focus:border-forest-green focus:ring-1 focus:ring-forest-green outline-none"
              />
            </div>
          </div>
        </div>

        {auditLoading ? (
          <p className="text-sm text-pine-mid">Loading audit logs...</p>
        ) : auditLogs.length === 0 ? (
          <p className="text-sm text-pine-mid">No audit entries found.</p>
        ) : (
          <div className="overflow-x-auto border border-sage-mid rounded-lg">
            <table className="min-w-full text-sm text-left">
              <thead className="bg-sage-light text-pine-mid text-xs uppercase">
                <tr>
                  <th className="px-3 py-2">Time</th>
                  <th className="px-3 py-2">Action</th>
                  <th className="px-3 py-2">Actor</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">IP</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} className="border-t border-sage-mid">
                    <td className="px-3 py-2 text-pine-mid">
                      {formatDateTime(log.created_at, {
                        timeZone,
                        dateFormat,
                        timeFormat,
                        locale,
                        includeSeconds: true,
                      })}
                    </td>
                    <td className="px-3 py-2 text-pine-deep font-medium">{log.action}</td>
                    <td className="px-3 py-2 text-pine-mid">
                      {log.actor_email || log.actor_user_id || '—'}
                    </td>
                    <td className="px-3 py-2 text-pine-mid">
                      {log.target_type ? `${log.target_type}:${log.target_id ?? '—'}` : '—'}
                    </td>
                    <td className="px-3 py-2 text-pine-mid">{log.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex items-center justify-between mt-4">
          <span className="text-xs text-pine-mid">
            Showing {auditLogs.length} of {auditTotal}
          </span>
          <div className="flex items-center gap-2 text-xs text-pine-mid">
            <button
              type="button"
              onClick={() => handleAuditPageChange(auditPage - 1)}
              disabled={auditPage <= 1}
              className="px-2 py-1 border border-sage-mid rounded disabled:opacity-50"
            >
              Prev
            </button>
            <span>
              Page {auditPage} of {auditPageCount}
            </span>
            <button
              type="button"
              onClick={() => handleAuditPageChange(auditPage + 1)}
              disabled={auditPage >= auditPageCount}
              className="px-2 py-1 border border-sage-mid rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </Card>

      <Card>
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-lg font-medium text-pine-deep">System Logs</h2>
            <p className="text-sm text-pine-mid">
              Download backend log files for troubleshooting and audits.
            </p>
          </div>
          <button
            type="button"
            onClick={loadSystemLogs}
            className="px-4 py-2 border border-sage-mid rounded-lg text-sm text-pine-deep hover:border-forest-green"
          >
            Refresh
          </button>
        </div>

        {systemLoading ? (
          <p className="text-sm text-pine-mid">Loading system logs...</p>
        ) : systemLogs.length === 0 ? (
          <p className="text-sm text-pine-mid">No log files found.</p>
        ) : (
          <div className="space-y-2">
            {systemLogs.map((log) => (
              <div
                key={log.name}
                className="flex items-center justify-between border border-sage-mid rounded-lg px-3 py-2"
              >
                <div>
                  <p className="text-sm text-pine-deep font-medium">{log.name}</p>
                  <p className="text-xs text-pine-mid">
                    {formatDateTime(log.modified_at, {
                      timeZone,
                      dateFormat,
                      timeFormat,
                      locale,
                      includeSeconds: true,
                    })}{' '}
                    | {(log.size_bytes / 1024).toFixed(1)} KB
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDownloadSystemLog(log.name)}
                  className="px-3 py-1 border border-sage-mid rounded text-xs text-pine-deep hover:border-forest-green"
                >
                  Download
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
