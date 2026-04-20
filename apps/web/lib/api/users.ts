import { apiFetch } from "@/lib/api";

export type Theme = "dark" | "light" | "system";

export type UserPreferences = {
  theme: Theme;
  locale: string | null;
};

export type UserPreferencesPatch = Partial<UserPreferences>;

export function getMyPreferences(): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/api/v1/users/me/preferences");
}

export function updateMyPreferences(
  body: UserPreferencesPatch,
): Promise<UserPreferences> {
  return apiFetch<UserPreferences>("/api/v1/users/me/preferences", {
    method: "PATCH",
    body,
  });
}
