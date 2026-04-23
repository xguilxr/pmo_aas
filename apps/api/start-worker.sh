#!/usr/bin/env bash
# US-048 — Wrapper del worker Celery con sidecar Tailscale.
#
# Flujo:
#  1. Arranca `tailscaled` en user-space networking (Railway NO da /dev/net/tun).
#  2. Ejecuta `tailscale up` con un TS_AUTHKEY reusable + ephemeral
#     (ver docs/archive/runbooks-ai-legacy/local-ollama-setup.md §7 —
#     runbook archivado post-DEC-017 porque Groq reemplazó Ollama en el
#     flujo productivo; este script queda solo para tenants BYO legacy
#     con Ollama propio). El peer se llama `railway-worker` con tag
#     `tag:railway-worker`.
#  3. `exec` a Celery — si tailscaled muere después, el container muere
#     también y Railway lo reinicia (restartPolicy en worker.railway.toml).
set -euo pipefail

TS_SOCKET="/tmp/tailscaled.sock"
TS_STATE="mem:"  # state en memoria — al morir el peer, TS admin lo borra (ephemeral)
TS_HOSTNAME="${TS_HOSTNAME:-railway-worker}"

if [[ -z "${TS_AUTHKEY:-}" ]]; then
  echo "FATAL: TS_AUTHKEY no configurado. Ver RAILWAY_SETUP.md §worker" >&2
  echo "  → generar en https://login.tailscale.com/admin/settings/keys" >&2
  echo "  → reusable + ephemeral + tag:railway-worker" >&2
  exit 1
fi

echo "[start-worker] arrancando tailscaled (user-space)…"
/usr/sbin/tailscaled \
  --tun=userspace-networking \
  --state="${TS_STATE}" \
  --socket="${TS_SOCKET}" \
  &
TSD_PID=$!

# Espera a que el socket esté vivo (máx ~5 s)
for _ in $(seq 1 10); do
  if [[ -S "${TS_SOCKET}" ]]; then
    break
  fi
  sleep 0.5
done
if [[ ! -S "${TS_SOCKET}" ]]; then
  echo "FATAL: tailscaled no creó el socket en ${TS_SOCKET} tras 5 s" >&2
  kill "${TSD_PID}" 2>/dev/null || true
  exit 1
fi

echo "[start-worker] uniéndose al tailnet como ${TS_HOSTNAME}…"
tailscale --socket="${TS_SOCKET}" up \
  --authkey="${TS_AUTHKEY}" \
  --hostname="${TS_HOSTNAME}" \
  --accept-dns=true

echo "[start-worker] tailscale status:"
tailscale --socket="${TS_SOCKET}" status || true

# Exportamos la ruta al socket por si otras utilidades del container
# quieren usar `tailscale --socket=...`. El cliente HTTP de Python usa
# MagicDNS resuelto por el resolver local, no necesita el socket.
export TS_SOCKET

echo "[start-worker] exec celery…"
exec celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
