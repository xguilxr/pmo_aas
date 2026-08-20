// US-221 — cliente del plan de suscripción.
//
// Solo lectura del lado del inquilino: el artboard es explícito —«sin paywall ni
// billing en esta fase»— y el `enforced: false` de la respuesta lo dice en el
// contrato, no solo en la documentación.
import { apiFetch } from "@/lib/api";

export type Tier = "free" | "pro" | "enterprise";

// Qué le pasa a un recurso frente a su tope. `sin_limite` **no** es un tope de
// cero: un cero diría «no puedes crear ninguna», que es lo contrario de «no hay
// tope» (DAT-12).
export type EstadoDeUso = "sin_limite" | "dentro" | "al_limite" | "excedido";

export type UsoDelPlan = {
  key: string;
  label: string;
  used: number;
  // `null` = sin tope declarado. Los números de cada tier no están en ningún
  // documento del repositorio, así que se capturan por inquilino.
  limit: number | null;
  state: EstadoDeUso;
  percent: number | null;
};

export type EstadoDelPlan = {
  tier: Tier;
  tier_label: string;
  enforced: boolean;
  usage: UsoDelPlan[];
  over_limit: boolean;
  // Cuántos recursos no tienen tope. Va aparte porque «todo dentro del plan» con
  // cuatro límites sin declarar no significa nada.
  undeclared_limits: number;
  state_labels: Record<string, string>;
  consequences: Record<string, string>;
  note: string;
};

export const getPlan = () => apiFetch<EstadoDelPlan>("/api/v1/admin/plan");
