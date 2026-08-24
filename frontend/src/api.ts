export type Health = {
  status: string;
  database: string;
};

export type ResourceCounts = {
  providers: number;
  categories: number;
  expenses: number;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error("The Cost Review API is unavailable.");
  }
  return response.json() as Promise<T>;
}

export async function loadFoundation(): Promise<{
  health: Health;
  counts: ResourceCounts;
}> {
  const [health, providers, categories, expenses] = await Promise.all([
    getJson<Health>("/api/v1/health"),
    getJson<unknown[]>("/api/v1/providers"),
    getJson<unknown[]>("/api/v1/categories"),
    getJson<unknown[]>("/api/v1/expenses"),
  ]);

  return {
    health,
    counts: {
      providers: providers.length,
      categories: categories.length,
      expenses: expenses.length,
    },
  };
}
