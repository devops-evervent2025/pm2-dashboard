"use client";

import { LoadingState } from "@/components/Preloader";
import { UnifiedRepo } from "@/components/EnvRepoGroupModal";

function parseGroupLabel(label: string): { server: string; env: string } {
  const parts = label.split(" · ");
  if (parts.length >= 2) {
    return { server: parts[0], env: parts.slice(1).join(" · ") };
  }
  return { server: label, env: "All repositories" };
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path
        fillRule="evenodd"
        d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function ServerStackIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
      <path d="M2 4.5A1.5 1.5 0 013.5 3h13A1.5 1.5 0 0118 4.5v2A1.5 1.5 0 0116.5 8h-13A1.5 1.5 0 012 6.5v-2zM2 13.5A1.5 1.5 0 013.5 12h13a1.5 1.5 0 011.5 1.5v2a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 012 15.5v-2z" />
    </svg>
  );
}

export default function RepoGroupList({
  clientName,
  groupedRepos,
  loading,
  searchQuery,
  onSearchChange,
  onOpenGroup,
}: {
  clientName: string;
  groupedRepos: [string, UnifiedRepo[]][];
  loading: boolean;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onOpenGroup: (label: string, repos: UnifiedRepo[]) => void;
}) {
  const totalRepos = groupedRepos.reduce((sum, [, repos]) => sum + repos.length, 0);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900">
        <div className="flex flex-col gap-3 border-b border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5 dark:border-slate-800">
          <div className="min-w-0 shrink-0">
            <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
              Environment groups
            </p>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{clientName}</h2>
          </div>

          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center sm:gap-3">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {groupedRepos.length} groups
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
                {totalRepos} repos
              </span>
            </div>

            <div className="relative w-full sm:w-72 lg:w-80">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5 text-slate-400 dark:text-slate-500">
                <SearchIcon />
              </div>
              <input
                type="text"
                placeholder="Search repos…"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="block w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500"
              />
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3 sm:p-4">
          {loading && (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 dark:border-slate-800 dark:bg-slate-950/40">
              <LoadingState message="Loading repos" variant="compact" />
            </div>
          )}

          {!loading && groupedRepos.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center dark:border-slate-700 dark:bg-slate-950/30">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                <SearchIcon />
              </div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {searchQuery.trim() ? `No repos match "${searchQuery}"` : "No repos found for this client"}
              </p>
            </div>
          )}

          {!loading && groupedRepos.length > 0 && (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {groupedRepos.map(([label, repos]) => {
                const { server, env } = parseGroupLabel(label);

                return (
                  <button
                    key={label}
                    type="button"
                    onClick={() => onOpenGroup(label, repos)}
                    className="group flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-3 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800/70"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-500 transition-colors group-hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                      <ServerStackIcon />
                    </span>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[10px] font-medium uppercase tracking-wider text-slate-500">
                        {server}
                      </p>
                      <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{env}</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {repos.length} repo{repos.length === 1 ? "" : "s"}
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-col items-center gap-1">
                      <span className="inline-flex min-w-[1.75rem] items-center justify-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                        {repos.length}
                      </span>
                      <span className="flex h-7 w-7 items-center justify-center rounded-full text-slate-400 transition-all group-hover:bg-brand-500 group-hover:text-white">
                        <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                          <path
                            fillRule="evenodd"
                            d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.06-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
