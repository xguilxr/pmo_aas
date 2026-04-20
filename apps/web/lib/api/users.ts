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

export type MyProfile = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
};

export type MyProfilePatch = { full_name?: string };

export function getMyProfile(): Promise<MyProfile> {
  return apiFetch<MyProfile>("/api/v1/users/me");
}

export function updateMyProfile(body: MyProfilePatch): Promise<MyProfile> {
  return apiFetch<MyProfile>("/api/v1/users/me", { method: "PATCH", body });
}
