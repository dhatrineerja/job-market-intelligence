"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; database: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold">Job Market Intelligence</h1>
      <p className="text-lg" data-testid="api-status">
        {error
          ? "API: unreachable"
          : health
            ? `API: ${health.status === "ok" ? "healthy" : health.status} (database ${health.database})`
            : "API: checking..."}
      </p>
    </main>
  );
}
