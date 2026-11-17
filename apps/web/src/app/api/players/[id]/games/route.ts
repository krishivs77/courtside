import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return NextResponse.json({ error: "Invalid player ID" }, { status: 400 });
  const url = new URL(`/api/v1/players/${id}/games`, process.env.API_BASE_URL ?? "http://127.0.0.1:8000");
  for (const key of ["limit", "offset", "season"]) {
    const value = request.nextUrl.searchParams.get(key);
    if (value !== null) url.searchParams.set(key, value);
  }
  try {
    const response = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (response.status === 404) return NextResponse.json({ error: "Player not found" }, { status: 404 });
    if (response.status === 422) return NextResponse.json({ error: "Invalid game-log filters" }, { status: 422 });
    if (!response.ok) throw new Error("Backend unavailable");
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Game logs are temporarily unavailable" }, { status: 502 });
  }
}
