import Link from "next/link";
import PlayerSearch from "@/components/players/PlayerSearch";

export default function PlayersPage() {
  return (
    <main className="min-h-screen bg-[#080c14] text-white">
      <div className="mx-auto max-w-7xl px-6 py-8">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <Link href="/" className="text-2xl font-black">
            COURTSIDE<span className="text-orange-500">.</span>
          </Link>

          <nav className="flex gap-6 text-sm text-slate-400">
            <Link href="/teams" className="hover:text-white">
              Teams
            </Link>
            <Link href="/players" className="text-orange-400">
              Players
            </Link>
          </nav>
        </header>

        <section className="pb-10 pt-14">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-orange-500">
            Player Directory
          </p>

          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Know the <span className="text-orange-500">players.</span>
          </h1>

          <p className="mt-4 max-w-2xl text-slate-400">
            Search the NBA player database. Explore player profiles,
            identities, and imported game-by-game performance.
          </p>
        </section>

        <PlayerSearch />
      </div>
    </main>
  );
}
