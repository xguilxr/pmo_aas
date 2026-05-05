const ALPHABET = "abcdefghijkmnopqrstuvwxyz";
const ALPHABET_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const DIGITS = "23456789";
const SYMBOLS = "!@#$%&*";

export function generatePassword(length = 16): string {
  const all = ALPHABET + ALPHABET_UPPER + DIGITS + SYMBOLS;
  const required = [
    pick(ALPHABET_UPPER),
    pick(ALPHABET),
    pick(DIGITS),
    pick(SYMBOLS),
  ];
  const rest = Array.from({ length: Math.max(length - required.length, 0) }, () => pick(all));
  return shuffle([...required, ...rest]).join("");
}

function pick(s: string): string {
  const arr = new Uint32Array(1);
  crypto.getRandomValues(arr);
  return s[arr[0] % s.length];
}

function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const r = new Uint32Array(1);
    crypto.getRandomValues(r);
    const j = r[0] % (i + 1);
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export type PolicyCheck = { label: string; ok: boolean };

export function checkPasswordPolicy(pwd: string): PolicyCheck[] {
  const symbols = /[!@#$%^&*()\-_=+[\]{};:,.<>/?|`~'"\\]/;
  return [
    { label: "Al menos 8 caracteres", ok: pwd.length >= 8 },
    { label: "Una letra mayúscula", ok: /[A-Z]/.test(pwd) },
    { label: "Un dígito", ok: /\d/.test(pwd) },
    { label: "Un símbolo", ok: symbols.test(pwd) },
  ];
}

export function passwordPolicyOk(pwd: string): boolean {
  return checkPasswordPolicy(pwd).every((c) => c.ok);
}
