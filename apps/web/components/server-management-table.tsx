"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  MonitorCog,
  Pause,
  Play,
  Power,
  RotateCcw,
  ServerIcon,
  X,
} from "lucide-react";

export interface Server {
  id: string;
  number: string;
  serviceName: string;
  osType: "windows" | "linux" | "ubuntu";
  serviceLocation: string;
  countryCode: "de" | "us" | "fr" | "jp";
  ip: string;
  dueDate: string;
  cpuPercentage: number;
  status: "active" | "paused" | "inactive";
}

interface ServerManagementTableProps {
  title?: string;
  servers?: Server[];
  onStatusChange?: (serverId: string, newStatus: Server["status"]) => void;
  className?: string;
}

const defaultServers: Server[] = [
  {
    id: "1",
    number: "01",
    serviceName: "VPS-2 (Windows)",
    osType: "windows",
    serviceLocation: "Frankfurt, Germany",
    countryCode: "de",
    ip: "198.51.100.211",
    dueDate: "14 Oct 2027",
    cpuPercentage: 80,
    status: "active",
  },
  {
    id: "2",
    number: "02",
    serviceName: "VPS-1 (Windows)",
    osType: "windows",
    serviceLocation: "Frankfurt, Germany",
    countryCode: "de",
    ip: "203.0.113.158",
    dueDate: "14 Oct 2027",
    cpuPercentage: 90,
    status: "active",
  },
  {
    id: "3",
    number: "03",
    serviceName: "VPS-1 (Ubuntu)",
    osType: "ubuntu",
    serviceLocation: "Paris, France",
    countryCode: "fr",
    ip: "192.0.2.37",
    dueDate: "27 Jun 2027",
    cpuPercentage: 50,
    status: "paused",
  },
  {
    id: "4",
    number: "04",
    serviceName: "Cloud Server (Ubuntu)",
    osType: "ubuntu",
    serviceLocation: "California, US West",
    countryCode: "us",
    ip: "198.51.100.23",
    dueDate: "30 May 2030",
    cpuPercentage: 95,
    status: "active",
  },
  {
    id: "5",
    number: "05",
    serviceName: "Dedicated Server (Windows)",
    osType: "windows",
    serviceLocation: "Virginia, US East",
    countryCode: "us",
    ip: "203.0.113.45",
    dueDate: "15 Dec 2026",
    cpuPercentage: 25,
    status: "inactive",
  },
];

function getStatusClasses(status: Server["status"]) {
  switch (status) {
    case "active":
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
    case "paused":
      return "border-amber-200 bg-amber-50 text-amber-700";
    case "inactive":
      return "border-rose-200 bg-rose-50 text-rose-700";
  }
}

function getOsLabel(osType: Server["osType"]) {
  switch (osType) {
    case "windows":
      return "Windows";
    case "ubuntu":
      return "Ubuntu";
    case "linux":
      return "Linux";
  }
}

function getCpuTone(cpuPercentage: number) {
  if (cpuPercentage >= 85) {
    return "bg-rose-500";
  }
  if (cpuPercentage >= 60) {
    return "bg-amber-500";
  }
  return "bg-emerald-500";
}

function CpuMeter({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${getCpuTone(value)}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-12 text-right font-mono text-sm text-foreground">
        {value}%
      </span>
    </div>
  );
}

function StatusBadge({ status }: { status: Server["status"] }) {
  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] ${getStatusClasses(status)}`}
    >
      {status}
    </span>
  );
}

export function ServerManagementTable({
  title = "Active Services",
  servers: initialServers = defaultServers,
  onStatusChange,
  className = "",
}: ServerManagementTableProps = {}) {
  const [servers, setServers] = useState<Server[]>(initialServers);
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);

  const selectedServer = selectedServerId
    ? servers.find((server) => server.id === selectedServerId) ?? null
    : null;

  const handleStatusChange = (
    serverId: string,
    newStatus: Server["status"],
  ) => {
    onStatusChange?.(serverId, newStatus);
    setServers((currentServers) =>
      currentServers.map((server) =>
        server.id === serverId ? { ...server, status: newStatus } : server,
      ),
    );
  };

  const activeCount = servers.filter((server) => server.status === "active").length;
  const inactiveCount = servers.filter(
    (server) => server.status === "inactive",
  ).length;

  return (
    <div className={`mx-auto w-full max-w-7xl ${className}`}>
      <div className="relative overflow-hidden rounded-[1.75rem] border border-border/60 bg-background shadow-[0_24px_70px_-48px_rgba(16,30,24,0.24)]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/50 px-6 py-5">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-muted/45">
                <ServerIcon className="size-4 text-muted-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground">
                  {activeCount} active - {inactiveCount} inactive
                </p>
              </div>
            </div>
          </div>
          <StatusBadge status="active" />
        </div>

        <div className="grid grid-cols-[0.7fr_2fr_2fr_1.4fr_1.2fr_1.3fr] gap-4 border-b border-border/40 px-6 py-3 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
          <div>No</div>
          <div>Service</div>
          <div>Location</div>
          <div>IP</div>
          <div>CPU</div>
          <div>Status</div>
        </div>

        <div className="divide-y divide-border/35">
          {servers.map((server) => (
            <button
              key={server.id}
              type="button"
              onClick={() => setSelectedServerId(server.id)}
              className="grid w-full grid-cols-[0.7fr_2fr_2fr_1.4fr_1.2fr_1.3fr] gap-4 px-6 py-4 text-left transition-colors hover:bg-muted/35"
            >
              <div className="text-lg font-semibold text-muted-foreground">
                {server.number}
              </div>
              <div className="space-y-1">
                <p className="font-medium text-foreground">{server.serviceName}</p>
                <p className="text-sm text-muted-foreground">
                  {getOsLabel(server.osType)}
                </p>
              </div>
              <div className="space-y-1">
                <p className="text-foreground">{server.serviceLocation}</p>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  {server.countryCode}
                </p>
              </div>
              <div className="font-mono text-sm text-foreground">{server.ip}</div>
              <CpuMeter value={server.cpuPercentage} />
              <div className="flex items-center">
                <StatusBadge status={server.status} />
              </div>
            </button>
          ))}
        </div>

        <AnimatePresence>
          {selectedServer ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10 bg-background/90 backdrop-blur-sm"
            >
              <motion.div
                initial={{ y: 16, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: 16, opacity: 0 }}
                className="flex h-full flex-col"
              >
                <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border/50 px-6 py-5">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-full border border-border/70 bg-muted/45">
                        <MonitorCog className="size-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                          Server {selectedServer.number}
                        </p>
                        <h4 className="text-xl font-semibold text-foreground">
                          {selectedServer.serviceName}
                        </h4>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      <StatusBadge status={selectedServer.status} />
                      <span className="inline-flex rounded-full border border-border/70 bg-background px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        {selectedServer.serviceLocation}
                      </span>
                      <span className="inline-flex rounded-full border border-border/70 bg-background px-3 py-1 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Due {selectedServer.dueDate}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {selectedServer.status === "active" ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700"
                        onClick={() =>
                          handleStatusChange(selectedServer.id, "inactive")
                        }
                      >
                        <Power className="size-4" />
                        Stop
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700"
                        onClick={() =>
                          handleStatusChange(selectedServer.id, "active")
                        }
                      >
                        <Play className="size-4" />
                        Start
                      </button>
                    )}

                    {selectedServer.status === "paused" ? (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700"
                        onClick={() =>
                          handleStatusChange(selectedServer.id, "active")
                        }
                      >
                        <Play className="size-4" />
                        Resume
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700"
                        onClick={() =>
                          handleStatusChange(selectedServer.id, "paused")
                        }
                      >
                        <Pause className="size-4" />
                        Pause
                      </button>
                    )}

                    <button
                      type="button"
                      className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background px-4 py-2 text-sm font-medium text-foreground"
                      onClick={() => {
                        handleStatusChange(selectedServer.id, "inactive");
                        window.setTimeout(() => {
                          handleStatusChange(selectedServer.id, "active");
                        }, 600);
                      }}
                    >
                      <RotateCcw className="size-4" />
                      Restart
                    </button>

                    <button
                      type="button"
                      className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-background text-foreground"
                      onClick={() => setSelectedServerId(null)}
                    >
                      <X className="size-4" />
                    </button>
                  </div>
                </div>

                <div className="grid flex-1 gap-4 px-6 py-5 md:grid-cols-[1.2fr_1fr]">
                  <div className="space-y-4">
                    <div className="rounded-[1.25rem] border border-border/60 bg-muted/25 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Resource load
                      </p>
                      <div className="mt-4">
                        <CpuMeter value={selectedServer.cpuPercentage} />
                      </div>
                    </div>

                    <div className="rounded-[1.25rem] border border-border/60 bg-muted/25 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Recent activity
                      </p>
                      <div className="mt-4 space-y-2 font-mono text-xs text-muted-foreground">
                        <p>[15:42:31] Server started successfully</p>
                        <p>[15:42:25] System health check passed</p>
                        <p>[15:41:18] CPU usage: {selectedServer.cpuPercentage}%</p>
                        <p>[15:40:05] Connection from {selectedServer.ip}</p>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-[1.25rem] border border-border/60 bg-muted/25 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Network
                      </p>
                      <dl className="mt-4 space-y-3 text-sm">
                        <div className="flex items-center justify-between gap-4">
                          <dt className="text-muted-foreground">IP address</dt>
                          <dd className="font-mono text-foreground">
                            {selectedServer.ip}
                          </dd>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <dt className="text-muted-foreground">Region</dt>
                          <dd className="text-foreground">
                            {selectedServer.serviceLocation}
                          </dd>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <dt className="text-muted-foreground">OS</dt>
                          <dd className="text-foreground">
                            {getOsLabel(selectedServer.osType)}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div className="rounded-[1.25rem] border border-border/60 bg-muted/25 p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Billing
                      </p>
                      <dl className="mt-4 space-y-3 text-sm">
                        <div className="flex items-center justify-between gap-4">
                          <dt className="text-muted-foreground">Renewal</dt>
                          <dd className="text-foreground">
                            {selectedServer.dueDate}
                          </dd>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <dt className="text-muted-foreground">Status</dt>
                          <dd>
                            <StatusBadge status={selectedServer.status} />
                          </dd>
                        </div>
                      </dl>
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
