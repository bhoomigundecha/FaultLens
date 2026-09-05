'use client';

/**
 * useFaultLens
 *
 * Polls the FaultLens backend every POLL_INTERVAL_MS and returns:
 *   incidents  — list of all incidents, newest first
 *   services   — list of all registered services
 *   loading    — true only on the very first fetch
 *   error      — last fetch error message (null when healthy)
 *   lastUpdated — Date of most recent successful fetch
 *
 * All JSONB columns (causal_path, metric_anomalies, log_anomalies,
 * trace_anomalies, ranked_suspects) are parsed to arrays/objects so
 * components never have to JSON.parse themselves.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE        = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
const POLL_INTERVAL   = 10_000; // 10 s

// ── Helpers ────────────────────────────────────────────────────────────────

function safeParse(value, fallback = []) {
  if (value === null || value === undefined) return fallback;
  if (typeof value !== 'string') return value;
  try { return JSON.parse(value); } catch { return fallback; }
}

function normaliseIncident(raw) {
  return {
    ...raw,
    causal_path:      safeParse(raw.causal_path,      []),
    metric_anomalies: safeParse(raw.metric_anomalies, []),
    log_anomalies:    safeParse(raw.log_anomalies,    []),
    trace_anomalies:  safeParse(raw.trace_anomalies,  []),
    ranked_suspects:  safeParse(raw.ranked_suspects,  []),
  };
}

async function fetchJSON(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Hook ───────────────────────────────────────────────────────────────────

export function useFaultLens() {
  const [incidents,    setIncidents]    = useState([]);
  const [services,     setServices]     = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);
  const [lastUpdated,  setLastUpdated]  = useState(null);

  // Track whether component is still mounted
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      const [rawIncidents, rawServices] = await Promise.all([
        fetchJSON(`${API_BASE}/v1/incidents?limit=50`),
        fetchJSON(`${API_BASE}/v1/services`),
      ]);

      if (!mounted.current) return;

      setIncidents(rawIncidents.map(normaliseIncident));
      setServices(rawServices);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      if (!mounted.current) return;
      setError(err.message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchAll]);

  return { incidents, services, loading, error, lastUpdated, refetch: fetchAll };
}
