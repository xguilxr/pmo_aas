export type LoginRequest = { identifier: string; password: string };
export type UserOut = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  roles: string[];
};
export type LoginResponse = { access_token: string; user: UserOut; tenants: string[] };

export class PmoaasClient {
  constructor(private baseUrl: string, private accessToken?: string) {}

  async login(body: LoginRequest): Promise<LoginResponse> {
    const r = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      credentials: "include",
    });
    if (!r.ok) throw new Error(`login_failed:${r.status}`);
    return r.json();
  }

  async me(): Promise<UserOut> {
    const r = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
      headers: { authorization: `Bearer ${this.accessToken}` },
    });
    if (!r.ok) throw new Error(`me_failed:${r.status}`);
    return r.json();
  }
}
