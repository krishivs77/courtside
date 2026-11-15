import { getHealth } from "@/lib/api";

export default async function Home() {
  let apiOnline = false;
  let apiVersion = "Unknown";

  try {
    const health = await getHealth();
    apiOnline = health.status === "healthy";
    apiVersion = health.version;
  } catch {
    apiOnline = false;
  }

  return (
    <main className="min-h-screen bg-[#080c14] px-6 py-12 text-white">
      <div className="mx-auto max-w-6xl">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <div>
            <h1 className="text-3xl font-black tracking-tight">
              COURTSIDE<span className="text-orange-500">.</span>
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              NBA Analytics & Intelligence
            </p>
          </div>
          <span className="rounded-full border border-white/10 px-4 py-2 text-xs text-slate-300">
            v0.1.0
          </span>
        </header>

        <section className="py-16">
          <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-orange-500">
            Welcome to COURTSIDE
          </p>

          <h2 className="max-w-3xl text-5xl font-bold tracking-tight">
            Basketball is a game of numbers.
            <span className="text-slate-500">
              {" "}Let&apos;s understand them.
            </span>
          </h2>

          <p className="mt-6 max-w-xl text-slate-400">
            Explore NBA performance, discover statistical trends,
            and understand the game through data.
          </p>
          <a
            href="/teams"
            className="mt-8 inline-flex rounded-xl bg-orange-500 px-6 py-3 text-sm font-bold text-black transition hover:bg-orange-400"
          >
            Explore NBA Teams
          </a>
        </section>

        <section className="rounded-2xl border border-white/10 bg-white/5 p-6">
          <h3 className="text-lg font-semibold">System Status</h3>

          <div className="mt-5 flex items-center gap-3">
            <span
              className={`h-3 w-3 rounded-full ${
                apiOnline ? "bg-green-400" : "bg-red-400"
              }`}
            />
            <span className="font-medium">
              FastAPI Backend: {apiOnline ? "Connected" : "Offline"}
            </span>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            API Version: {apiVersion}
          </p>
        </section>
      </div>
    </main>
  );
}
