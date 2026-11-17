import Link from "next/link";
import PlayerAnalytics from "@/components/players/PlayerAnalytics";

export default async function PlayerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <main className="min-h-screen bg-[#080c14] text-white">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <header className="flex items-center justify-between gap-4 border-b border-white/10 pb-6">
          <Link href="/" className="text-2xl font-black">COURTSIDE<span className="text-orange-500">.</span></Link>
          <nav className="flex gap-5 text-sm text-slate-400" aria-label="Main navigation">
            <Link href="/teams">Teams</Link><Link href="/players" className="text-orange-400">Players</Link>
          </nav>
        </header>
        <Link href="/players" className="mt-8 inline-block text-sm text-slate-400 hover:text-white">← Player directory</Link>
        <PlayerAnalytics id={id} />
      </div>
    </main>
  );
}
