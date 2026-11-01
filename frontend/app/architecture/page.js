'use client';

/* ─────────────────────────────────────────────────────────────────
   FaultLens Architecture Diagram
   Standalone page at /architecture
   Three annotated sections matching the demo script:
     1. Ingestion pipeline  (OTel → Kafka → Storage)
     2. LangGraph 6-agent workflow
     3. Neo4j + PageRank callout
───────────────────────────────────────────────────────────────── */

// ── tiny reusables ────────────────────────────────────────────────

function Arrow({ label, vertical = false }) {
  return (
    <div style={{
      display: 'flex', flexDirection: vertical ? 'column' : 'row',
      alignItems: 'center', gap: 2,
      color: '#94a3b8', flexShrink: 0,
    }}>
      {!vertical && (
        <>
          <div style={{ height: 1.5, width: 28, background: '#cbd5e1' }} />
          <span style={{ fontSize: 13, lineHeight: 1 }}>›</span>
        </>
      )}
      {vertical && (
        <>
          <div style={{ width: 1.5, height: 18, background: '#cbd5e1', margin: '0 auto' }} />
          <span style={{ fontSize: 13, lineHeight: 1 }}>↓</span>
        </>
      )}
      {label && (
        <span style={{
          position: 'absolute', fontSize: 9, color: '#94a3b8',
          whiteSpace: 'nowrap', marginTop: vertical ? 0 : -16,
        }}>{label}</span>
      )}
    </div>
  );
}

function Box({ icon, label, sub, color = '#2563eb', bg, border, wide = false, small = false }) {
  return (
    <div style={{
      background: bg ?? '#fff',
      border: `1.5px solid ${border ?? '#e2e8f0'}`,
      borderRadius: 12,
      padding: small ? '8px 12px' : '10px 14px',
      display: 'flex', alignItems: 'center', gap: 8,
      minWidth: wide ? 130 : small ? 80 : 100,
      boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
      flexShrink: 0,
    }}>
      <span style={{ fontSize: small ? 14 : 18, lineHeight: 1 }}>{icon}</span>
      <div>
        <p style={{ fontSize: small ? 10 : 11.5, fontWeight: 700, color: '#0b1f3a', margin: 0, lineHeight: 1.2 }}>{label}</p>
        {sub && <p style={{ fontSize: 9.5, color: '#64748b', margin: '2px 0 0 0', lineHeight: 1.2 }}>{sub}</p>}
      </div>
    </div>
  );
}

function SectionLabel({ number, text, color = '#2563eb' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
      <div style={{
        width: 22, height: 22, borderRadius: '50%',
        background: color, color: '#fff',
        fontSize: 11, fontWeight: 800,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>{number}</div>
      <span style={{ fontSize: 13, fontWeight: 700, color: '#0b1f3a' }}>{text}</span>
    </div>
  );
}

function CalloutBadge({ text, color = '#2563eb' }) {
  return (
    <div style={{
      background: color === '#7c3aed' ? '#f5f3ff' : '#eff6ff',
      border: `1px solid ${color === '#7c3aed' ? '#ddd6fe' : '#bfdbfe'}`,
      borderRadius: 8, padding: '6px 12px',
      fontSize: 11, fontWeight: 600,
      color: color, maxWidth: 280, lineHeight: 1.4,
      fontStyle: 'italic',
    }}>
      "{text}"
    </div>
  );
}

// ── Agent node ────────────────────────────────────────────────────
function AgentNode({ icon, name, desc, done = true, active = false }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
      width: 90,
    }}>
      <div style={{
        width: 42, height: 42, borderRadius: 12,
        background: active ? '#fef3c7' : done ? '#eff6ff' : '#f8fafc',
        border: `1.5px solid ${active ? '#fde68a' : done ? '#bfdbfe' : '#e2e8f0'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 18, position: 'relative',
        boxShadow: done ? '0 2px 8px rgba(37,99,235,0.10)' : 'none',
      }}>
        {icon}
        {done && (
          <div style={{
            position: 'absolute', top: -5, right: -5,
            width: 14, height: 14, borderRadius: '50%',
            background: '#10b981', border: '2px solid #fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 7, color: '#fff', fontWeight: 800,
          }}>✓</div>
        )}
      </div>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: 10, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>{name}</p>
        <p style={{ fontSize: 8.5, color: '#64748b', margin: '1px 0 0 0', lineHeight: 1.3 }}>{desc}</p>
      </div>
    </div>
  );
}

// ── Storage node ──────────────────────────────────────────────────
function StorageNode({ icon, name, sub, accent }) {
  return (
    <div style={{
      background: '#fff', border: `1.5px solid ${accent}22`,
      borderRadius: 10, padding: '10px 14px',
      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
      minWidth: 90, textAlign: 'center',
      boxShadow: `0 2px 10px ${accent}18`,
    }}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>{name}</p>
      <p style={{ fontSize: 8.5, color: '#64748b', margin: 0, lineHeight: 1.3 }}>{sub}</p>
    </div>
  );
}

// ── Main diagram ──────────────────────────────────────────────────
export default function ArchitecturePage() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(152deg,#cadcff 0%,#dae7fe 15%,#e8f0fe 35%,#f1f6ff 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 40, fontFamily: 'system-ui, sans-serif',
    }}>
      <div style={{ maxWidth: 960, width: '100%' }}>

        {/* ── Title ── */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 8 }}>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="14" stroke="#2563eb" strokeWidth="2" fill="none"/>
              <circle cx="16" cy="16" r="8"  stroke="#2563eb" strokeWidth="1.5" fill="none" strokeOpacity="0.4"/>
              <circle cx="16" cy="16" r="3"  fill="#2563eb"/>
              <line x1="16" y1="2"  x2="16" y2="6"  stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
              <line x1="16" y1="26" x2="16" y2="30" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
              <line x1="2"  y1="16" x2="6"  y2="16" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
              <line x1="26" y1="16" x2="30" y2="16" stroke="#2563eb" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <h1 style={{ fontSize: 26, fontWeight: 800, color: '#0b1f3a', margin: 0, letterSpacing: '-0.02em' }}>
              FaultLens — System Architecture
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#64748b', margin: 0 }}>
            Autonomous incident detection &amp; root cause analysis for microservice platforms
          </p>
        </div>

        {/* ══════════════════════════════════════════════════════
            SECTION 1 — Ingestion Pipeline
        ══════════════════════════════════════════════════════ */}
        <div style={{
          background: '#fff', borderRadius: 18,
          border: '1.5px solid #e2e8f0',
          padding: '22px 28px', marginBottom: 20,
          boxShadow: '0 4px 20px rgba(37,99,235,0.06)',
        }}>
          <SectionLabel number="1" text="Production-grade ingestion pipeline" />

          <div style={{ display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'wrap', rowGap: 12 }}>

            {/* ShopFlow services */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <p style={{ fontSize: 9.5, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 4px 0' }}>ShopFlow (demo app)</p>
              {[
                ['🌐', 'api-gateway'],
                ['📦', 'order-service'],
                ['💳', 'payment-service'],
                ['🤖', 'ai-service'],
              ].map(([icon, name]) => (
                <div key={name} style={{
                  background: '#f8fafc', border: '1px solid #e2e8f0',
                  borderRadius: 8, padding: '5px 10px',
                  display: 'flex', alignItems: 'center', gap: 6, minWidth: 130,
                }}>
                  <span style={{ fontSize: 12 }}>{icon}</span>
                  <span style={{ fontSize: 10.5, fontWeight: 600, color: '#475569' }}>{name}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 8.5, background: '#dcfce7', color: '#16a34a', borderRadius: 4, padding: '1px 5px', fontWeight: 700 }}>OTel SDK</span>
                </div>
              ))}
            </div>

            <Arrow />

            {/* OTel Collector */}
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
            }}>
              <div style={{
                background: '#eff6ff', border: '1.5px solid #bfdbfe',
                borderRadius: 12, padding: '14px 16px', textAlign: 'center', minWidth: 90,
              }}>
                <div style={{ fontSize: 22, marginBottom: 4 }}>📡</div>
                <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>OTel</p>
                <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>Collector</p>
                <p style={{ fontSize: 8.5, color: '#64748b', margin: '3px 0 0 0' }}>metrics · traces · logs</p>
                <p style={{ fontSize: 8.5, color: '#64748b', margin: 0 }}>gzip + protobuf</p>
              </div>
            </div>

            <Arrow />

            {/* Kafka / Redpanda */}
            <div style={{
              background: '#fff8f0', border: '1.5px solid #fed7aa',
              borderRadius: 12, padding: '14px 16px', textAlign: 'center', minWidth: 90,
            }}>
              <div style={{ fontSize: 22, marginBottom: 4 }}>⚡</div>
              <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>Redpanda</p>
              <p style={{ fontSize: 8.5, color: '#64748b', margin: '3px 0 0 0' }}>Kafka-compatible</p>
              <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {['raw.metrics', 'raw.traces', 'raw.logs'].map(t => (
                  <span key={t} style={{ fontSize: 8, background: '#fff', border: '1px solid #fed7aa', borderRadius: 4, padding: '1px 5px', color: '#92400e', fontFamily: 'monospace' }}>{t}</span>
                ))}
              </div>
            </div>

            <Arrow />

            {/* FaultLens Ingestion API */}
            <div style={{
              background: '#f0fdf4', border: '1.5px solid #bbf7d0',
              borderRadius: 12, padding: '14px 16px', textAlign: 'center', minWidth: 90,
            }}>
              <div style={{ fontSize: 22, marginBottom: 4 }}>⚙️</div>
              <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>FaultLens</p>
              <p style={{ fontSize: 10.5, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>Ingestion API</p>
              <p style={{ fontSize: 8.5, color: '#64748b', margin: '3px 0 0 0' }}>FastAPI · port 8000</p>
              <p style={{ fontSize: 8.5, color: '#64748b', margin: 0 }}>protobuf + gzip decode</p>
            </div>

            <Arrow />

            {/* Storage backends */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <p style={{ fontSize: 9.5, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 4px 0' }}>Storage layer</p>
              <StorageNode icon="📊" name="TimescaleDB"  sub="metrics · hypertable"   accent="#2563eb" />
              <StorageNode icon="🔍" name="Elasticsearch" sub="logs · KNN embeddings" accent="#f59e0b" />
              <StorageNode icon="🕸️"  name="Neo4j"        sub="dependency graph"      accent="#7c3aed" />
              <StorageNode icon="🗄️"  name="PostgreSQL"   sub="incidents · state"     accent="#10b981" />
            </div>

          </div>

          <div style={{ marginTop: 14 }}>
            <CalloutBadge text="Production-grade ingestion. Not a toy pipeline." />
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════
            SECTION 2 — LangGraph 6-agent workflow
        ══════════════════════════════════════════════════════ */}
        <div style={{
          background: '#fff', borderRadius: 18,
          border: '1.5px solid #e2e8f0',
          padding: '22px 28px', marginBottom: 20,
          boxShadow: '0 4px 20px rgba(37,99,235,0.06)',
        }}>
          <SectionLabel number="2" text="LangGraph 6-agent autonomous workflow" />

          {/* Agent pipeline */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, overflowX: 'auto', paddingBottom: 8 }}>
            {[
              { icon: '🔭', name: 'Signal Scout',     desc: 'env assessment',     done: true  },
              { icon: '🧠', name: 'Anomaly Hunter',   desc: 'ML detection',       done: true  },
              { icon: '🕸️',  name: 'Graph Weaver',    desc: 'Neo4j traversal',    done: true  },
              { icon: '🔬', name: 'RCA Investigator', desc: 'ReAct LLM agent',    done: true  },
              { icon: '🗂️',  name: 'Triage',          desc: 'failure classifier', done: true  },
              { icon: '📝', name: 'Reporter',         desc: 'RCA report + save',  done: true  },
            ].map((agent, i, arr) => (
              <div key={agent.name} style={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                <AgentNode {...agent} />
                {i < arr.length - 1 && (
                  <div style={{ display: 'flex', alignItems: 'center', paddingBottom: 20 }}>
                    <div style={{ height: 1.5, width: 18, background: '#bfdbfe' }} />
                    <span style={{ fontSize: 12, color: '#93c5fd' }}>›</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* State flow annotation */}
          <div style={{
            marginTop: 14, padding: '10px 14px',
            background: '#f8fafc', borderRadius: 10,
            border: '1px solid #e2e8f0',
            display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13 }}>🔄</span>
              <span style={{ fontSize: 10.5, fontWeight: 600, color: '#475569' }}>
                Shared <code style={{ background: '#e2e8f0', padding: '1px 5px', borderRadius: 4, fontSize: 9.5 }}>FaultLensState</code> flows through all 6 nodes
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13 }}>💾</span>
              <span style={{ fontSize: 10.5, fontWeight: 600, color: '#475569' }}>
                Checkpointed to PostgreSQL via <code style={{ background: '#e2e8f0', padding: '1px 5px', borderRadius: 4, fontSize: 9.5 }}>AsyncPostgresSaver</code>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 13 }}>⚡</span>
              <span style={{ fontSize: 10.5, fontWeight: 600, color: '#475569' }}>
                LLM: Groq <code style={{ background: '#e2e8f0', padding: '1px 5px', borderRadius: 4, fontSize: 9.5 }}>openai/gpt-oss-120b</code>
              </span>
            </div>
          </div>

          {/* RCA Investigator callout — the key node */}
          <div style={{
            marginTop: 10, padding: '10px 14px',
            background: '#eff6ff', borderRadius: 10, border: '1px solid #bfdbfe',
            display: 'flex', alignItems: 'flex-start', gap: 10,
          }}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>🔬</span>
            <div>
              <p style={{ fontSize: 10.5, fontWeight: 700, color: '#1e40af', margin: '0 0 2px 0' }}>
                RCA Investigator — ReAct loop (max 8 iterations)
              </p>
              <p style={{ fontSize: 10, color: '#475569', margin: 0 }}>
                LLM autonomously calls tools:
                {' '}
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: 3, fontSize: 9 }}>query_metric_window</code>
                {' '}
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: 3, fontSize: 9 }}>get_service_dependencies</code>
                {' '}
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: 3, fontSize: 9 }}>run_pagerank</code>
                {' '}
                <code style={{ background: '#dbeafe', padding: '1px 4px', borderRadius: 3, fontSize: 9 }}>search_logs</code>
                {' '}
                — decides <em>what to investigate next</em> without any hardcoded logic
              </p>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <CalloutBadge text="Each agent has a specific job. State is checkpointed. The workflow is resumable." />
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════
            SECTION 3 — Neo4j + PageRank
        ══════════════════════════════════════════════════════ */}
        <div style={{
          background: '#fff', borderRadius: 18,
          border: '1.5px solid #e2e8f0',
          padding: '22px 28px',
          boxShadow: '0 4px 20px rgba(37,99,235,0.06)',
        }}>
          <SectionLabel number="3" text="Neo4j service graph + personalised PageRank" color="#7c3aed" />

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>

            {/* Service graph visualisation */}
            <div style={{ flex: 1, minWidth: 280 }}>
              <p style={{ fontSize: 9.5, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 10px 0' }}>
                Service dependency graph (built from distributed traces)
              </p>

              <div style={{ position: 'relative', height: 180 }}>
                {/* Nodes */}
                {[
                  { id: 'gw',  label: 'api-gateway',     x: 20,  y: 70,  color: '#10b981', score: 0.15 },
                  { id: 'ord', label: 'order-service',   x: 160, y: 30,  color: '#f59e0b', score: 0.22 },
                  { id: 'pay', label: 'payment-service', x: 300, y: 70,  color: '#ef4444', score: 0.89, root: true },
                  { id: 'inv', label: 'inventory-svc',   x: 160, y: 120, color: '#10b981', score: 0.08 },
                  { id: 'db',  label: 'database',        x: 440, y: 70,  color: '#ef4444', score: 0.71 },
                ].map(node => (
                  <div key={node.id} style={{
                    position: 'absolute', left: node.x, top: node.y,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                  }}>
                    <div style={{
                      width: node.root ? 52 : 44, height: node.root ? 52 : 44,
                      borderRadius: '50%',
                      background: node.root ? '#fef2f2' : '#f8fafc',
                      border: `2px solid ${node.color}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      position: 'relative',
                      boxShadow: node.root ? `0 0 16px ${node.color}44` : 'none',
                    }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: node.color }}>
                        {Math.round(node.score * 100)}
                      </span>
                      {node.root && (
                        <div style={{
                          position: 'absolute', top: -8, left: '50%', transform: 'translateX(-50%)',
                          background: '#ef4444', color: '#fff',
                          fontSize: 7, fontWeight: 800, padding: '1px 5px', borderRadius: 4,
                          whiteSpace: 'nowrap',
                        }}>ROOT CAUSE</div>
                      )}
                    </div>
                    <span style={{ fontSize: 8, fontWeight: 600, color: '#475569', whiteSpace: 'nowrap' }}>{node.label}</span>
                  </div>
                ))}

                {/* Edges (SVG) */}
                <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }} viewBox="0 0 540 190">
                  <defs>
                    <marker id="arr" markerWidth="5" markerHeight="5" refX="5" refY="2.5" orient="auto">
                      <path d="M0,0 L5,2.5 L0,5 Z" fill="#cbd5e1"/>
                    </marker>
                  </defs>
                  {/* gw → ord */}
                  <path d="M 66,92 L 172,55" stroke="#cbd5e1" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"/>
                  {/* gw → inv */}
                  <path d="M 66,98 L 172,138" stroke="#cbd5e1" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"/>
                  {/* ord → pay */}
                  <path d="M 218,52 L 312,82" stroke="#fca5a5" strokeWidth="2" fill="none" markerEnd="url(#arr)"/>
                  {/* pay → db */}
                  <path d="M 364,96 L 452,96" stroke="#fca5a5" strokeWidth="2" fill="none" markerEnd="url(#arr)"/>
                </svg>
              </div>

              <p style={{ fontSize: 9, color: '#94a3b8', margin: '4px 0 0 0', fontStyle: 'italic' }}>
                Numbers = personalised PageRank score (0–100). Red = anomalous.
              </p>
            </div>

            {/* PageRank explanation */}
            <div style={{ width: 220, flexShrink: 0 }}>
              <div style={{
                background: '#f5f3ff', border: '1.5px solid #ddd6fe',
                borderRadius: 12, padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <span style={{ fontSize: 18 }}>🔗</span>
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#5b21b6' }}>Personalised PageRank</span>
                </div>
                {[
                  { icon: '🌐', label: 'Google uses it', sub: 'to rank web pages by incoming links' },
                  { icon: '🕸️',  label: 'We apply it to', sub: 'service call graphs — error propagation = link weight' },
                  { icon: '📍', label: 'Seed = anomalous', sub: 'services from Isolation Forest detection' },
                  { icon: '🎯', label: 'Output = root cause', sub: 'highest-ranked node is the origin of failure' },
                ].map((item, i) => (
                  <div key={i} style={{
                    display: 'flex', gap: 8, alignItems: 'flex-start',
                    paddingBottom: i < 3 ? 8 : 0,
                    borderBottom: i < 3 ? '1px solid #ede9fe' : 'none',
                    marginBottom: i < 3 ? 8 : 0,
                  }}>
                    <span style={{ fontSize: 13, flexShrink: 0 }}>{item.icon}</span>
                    <div>
                      <p style={{ fontSize: 10, fontWeight: 700, color: '#5b21b6', margin: 0 }}>{item.label}</p>
                      <p style={{ fontSize: 9, color: '#6d28d9', margin: '1px 0 0 0', lineHeight: 1.3 }}>{item.sub}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 10 }}>
                <CalloutBadge
                  text="The same algorithm Google uses for search — applied to service dependency graphs."
                  color="#7c3aed"
                />
              </div>
            </div>

          </div>
        </div>

        {/* ── Footer ── */}
        <div style={{ textAlign: 'center', marginTop: 20 }}>
          <p style={{ fontSize: 11, color: '#94a3b8' }}>
            FaultLens · LangGraph · Groq · TimescaleDB · Elasticsearch · Neo4j · Redpanda · OpenTelemetry
          </p>
        </div>

      </div>
    </div>
  );
}
