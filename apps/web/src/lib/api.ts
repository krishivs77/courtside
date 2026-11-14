export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

const API_BASE_URL =
  process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });

  if (!response.ok) {
    throw new Error(`API returned HTTP ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
