export type ApiEnvelope<T> = {
  ok: boolean;
  data?: T;
  meta?: Record<string, unknown>;
  error?: string;
  code?: string;
  details?: unknown;
};

export type CatalogItem = {
  id: number;
  label: string;
  [key: string]: unknown;
};

export type Catalogs = Record<string, CatalogItem[]>;

export const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("maaq_demo_token");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {})
      }
    });
  } catch {
    throw new Error(`No se pudo conectar con el backend en ${API_URL}. Verifica que uvicorn este ejecutandose en el puerto 8000.`);
  }
  const payload = (await response.json().catch(() => ({
    ok: false,
    error: "La API no devolvio JSON valido"
  }))) as ApiEnvelope<T>;

  if (!response.ok || !payload.ok) {
    throw new Error(payload.error ?? `Error HTTP ${response.status}`);
  }

  return payload.data as T;
}
