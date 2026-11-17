import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const search = request.nextUrl.searchParams.get("search")?.trim();

  if (!search || search.length < 2 || search.length > 100) {
    return NextResponse.json(
      { error: "Search must contain 2 to 100 characters" },
      { status: 400 }
    );
  }

  try {
    const url = new URL("/api/v1/players", API_BASE_URL);
    url.searchParams.set("search", search);
    url.searchParams.set("limit", "50");

    const response = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error("Player lookup failed:", error);

    return NextResponse.json(
      { error: "Player search is temporarily unavailable" },
      { status: 502 }
    );
  }
}
