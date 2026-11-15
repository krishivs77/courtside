import Link from "next/link";
import { Suspense } from "react";

import TeamsExplorer, {
  type Team,
} from "@/components/teams/TeamsExplorer";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

async function fetchTeams(): Promise<Team[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/teams`, {
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });

  if (!response.ok) {
    throw new Error(`Teams API returned ${response.status}`);
  }

  return response.json() as Promise<Team[]>;
}

async function loadTeams(): Promise<{
  teams: Team[];
  error: boolean;
}> {
  try {
    const teams = await fetchTeams();
    return { teams, error: false };
  } catch (error) {
    console.error("Failed to load NBA teams:", error);
    return { teams: [], error: true };
  }
}

async function TeamsContent() {
  const { teams, error } = await loadTeams();

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-red-500/20 bg-red-500/5 p-6"
      >
        <h2 className="font-semibold text-red-300">
          Unable to load teams
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Make sure FastAPI and PostgreSQL are running.
          Refresh this page once the connection is restored.
        </p>
      </div>
    );
  }

  return <TeamsExplorer teams={teams} />;
}

function TeamsLoading() {
  return (
    <div
      role="status"
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    >
      {Array.from({ length: 8 }, (_, index) => (
        <div
          key={index}
          className="h-48 animate-pulse rounded-2xl border border-white/10 bg-white/5"
        />
      ))}
      <span className="sr-only">Loading NBA teams...</span>
    </div>
  );
}

export default function TeamsPage() {
  return (
    <main className="min-h-screen bg-[#080c14] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <Link
            href="/"
            className="text-2xl font-black tracking-tight"
          >
            COURTSIDE<span className="text-orange-500">.</span>
          </Link>

          <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
            NBA Intelligence
          </span>
        </header>

        <section className="pb-10 pt-12">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            League Directory
          </p>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Explore the <span className="text-orange-500">NBA.</span>
          </h1>

          <p className="mt-4 max-w-2xl text-slate-400">
            Discover all 30 NBA franchises. Search teams,
            explore conferences, and find the next matchup
            worth analyzing.
          </p>
        </section>

        <Suspense fallback={<TeamsLoading />}>
          <TeamsContent />
        </Suspense>
      </div>
    </main>
  );
}
