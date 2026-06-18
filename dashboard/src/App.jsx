import React, { useEffect, useMemo, useState } from 'react'

// ---- label dictionaries (data carries enums; UI carries the words) ----
const LEVEL_LABELS = {
  L1: '参数', L2: '结构', L3: '规则·信息', L4: '目标·范式',
}
const LEVEL_NOTE = {
  L1: '拧旋钮', L2: '改结构', L3: '改信息流/激励', L4: '改目标/范式',
}
const DELIV_LABELS = { high: '可近期交付', mid: '中等周期', low: '长线' }
const NOV_LABELS = { high: '高新颖', mid: '中等', low: '已有近似' }
const NOV_BADGE = { high: '★', mid: '◆', low: '·' }
const VP_LEVEL = { high: '高', mid: '中', low: '低' }

const OPERATOR_LABELS = {
  assumption_challenge: '挑战假设', reversal: '反转', actor_shift: '换行动者',
  decomposition: '分解', analogy: '类比', random_stimulus: '随机刺激',
  po: 'PO 挑衅', alternative_generation: '生成替代', constraint_removal: '去约束',
}

const SIZE_POS = { high: 1.0, mid: 0.66, low: 0.36 }

async function getJSON(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url}: ${r.status}`)
  return r.json()
}

function levelPos(v) {
  return { low: 0.15, mid: 0.5, high: 0.85 }[v] ?? 0.5
}

// dot radius in px from deliverability (bigger = more shippable / sooner)
function dotRadius(card) {
  const d = card?.value_profile?.deliverability || 'mid'
  return 9 + (SIZE_POS[d] ?? 0.66) * 13
}

function MetricChip({ label, value }) {
  return (
    <div className="chip">
      <span className="chip-label">{label}</span>
      <span className="chip-value">{value}</span>
    </div>
  )
}

// fan out dots that share a quantized (x,y) so a 3x3 value grid never stacks
// several ideas on one point — deterministic by list order, no randomness
function spreadPositions(survivors) {
  const groups = {}
  survivors.forEach((c) => {
    const bx = c.map_position?.x ?? levelPos(c.value_profile?.actionable_commercial)
    const by = c.map_position?.y ?? levelPos(c.value_profile?.conceptual_depth)
    const key = `${bx.toFixed(2)},${by.toFixed(2)}`
    if (!groups[key]) groups[key] = []
    groups[key].push({ c, bx, by })
  })
  const out = {}
  Object.values(groups).forEach((arr) => {
    if (arr.length === 1) {
      out[arr[0].c.id] = { x: arr[0].bx, y: arr[0].by }
      return
    }
    const R = 0.06 + Math.min(arr.length, 6) * 0.012
    arr.forEach((it, i) => {
      const ang = (Math.PI * 2 * i) / arr.length - Math.PI / 2
      const x = Math.min(0.95, Math.max(0.05, it.bx + R * Math.cos(ang)))
      const y = Math.min(0.95, Math.max(0.05, it.by + R * Math.sin(ang)))
      out[it.c.id] = { x, y }
    })
  })
  return out
}

// ---- the value map: continuous scatter, x=commercial, y=conceptual depth ----
function ValueMap({ map, cardsById, selected, onSelect }) {
  const W = 560, H = 560, PAD = 54
  const px = (x) => PAD + x * (W - 2 * PAD)
  const py = (y) => H - PAD - y * (H - 2 * PAD) // y up
  const origin = map.origin || { x: 0.15, y: 0.15 }
  const survivors = (map.survivors || []).map((id) => cardsById[id]).filter(Boolean)
  const positions = spreadPositions(survivors)

  return (
    <div className="map-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="map-svg" role="img"
           aria-label="价值地图：横轴商业行动性，纵轴概念深度">
        {/* quadrant grid */}
        <defs>
          <radialGradient id="dotGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(94,234,212,0.95)" />
            <stop offset="70%" stopColor="rgba(38,200,178,0.55)" />
            <stop offset="100%" stopColor="rgba(38,200,178,0.05)" />
          </radialGradient>
        </defs>
        <line x1={px(0.5)} y1={py(0)} x2={px(0.5)} y2={py(1)} className="map-mid" />
        <line x1={px(0)} y1={py(0.5)} x2={px(1)} y2={py(0.5)} className="map-mid" />
        <rect x={PAD} y={PAD} width={W - 2 * PAD} height={H - 2 * PAD} className="map-frame" />

        {/* axes labels */}
        <text x={W / 2} y={H - 14} className="axis-label" textAnchor="middle">
          {map.axes?.x?.label || '商业行动性'} →
        </text>
        <text x={18} y={H / 2} className="axis-label"
              textAnchor="middle" transform={`rotate(-90 18 ${H / 2})`}>
          {map.axes?.y?.label || '概念深度'} →
        </text>
        <text x={PAD} y={H - 30} className="axis-tick" textAnchor="start">
          {map.axes?.x?.low}
        </text>
        <text x={W - PAD} y={H - 30} className="axis-tick" textAnchor="end">
          {map.axes?.x?.high}
        </text>

        {/* origin marker (the paper's own incremental question) */}
        <g>
          <circle cx={px(origin.x)} cy={py(origin.y)} r={7} className="origin-dot" />
          <text x={px(origin.x) + 12} y={py(origin.y) + 4} className="origin-label">
            {origin.label || '原问题'}
          </text>
        </g>

        {/* survivor dots */}
        {survivors.map((c) => {
          const pos = positions[c.id] || { x: 0.5, y: 0.5 }
          const r = dotRadius(c)
          const isSel = selected === c.id
          const badge = NOV_BADGE[c.prior_art?.novelty_level] || '·'
          return (
            <g key={c.id} className={`map-dot ${isSel ? 'sel' : ''}`}
               transform={`translate(${px(pos.x)},${py(pos.y)})`}
               onClick={() => onSelect(c.id)} tabIndex={0}
               onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(c.id)}>
              <circle r={r + 6} className="dot-halo" />
              <circle r={r} className="dot-core" fill="url(#dotGlow)" />
              <text className="dot-badge" textAnchor="middle" dy={r + 15}>{badge}</text>
              {isSel && <circle r={r + 10} className="dot-ring" />}
            </g>
          )
        })}
      </svg>
      <p className="map-caption">
        点越大越快交付（可落地性）· 角标 ★/◆/· 标新颖度 · ◎ 原问题（增量改进角）·
        右上 = 既深又能落地
      </p>
    </div>
  )
}

function FloorBlock({ floor }) {
  if (!floor) return null
  const ok = floor.passes
  return (
    <div className={`floor ${ok ? 'floor-pass' : 'floor-fail'}`}>
      <div className="floor-head">
        <span className="floor-badge">{ok ? '通过证伪闸门' : '未过闸门'}</span>
      </div>
      {ok ? (
        <dl className="audit">
          <dt>最小实验</dt><dd>{floor.minimal_experiment}</dd>
          <dt>可证伪预测</dt><dd>{floor.falsifiable_prediction}</dd>
          <dt>对照</dt><dd>{floor.control}</dd>
        </dl>
      ) : (
        <p className="dim reject-reason">驳回理由：{floor.reject_reason}</p>
      )}
    </div>
  )
}

function CardView({ card, dofs }) {
  if (!card) return null
  const dof = (dofs || []).find((d) => d.id === card.parent_dof)
  const vp = card.value_profile || {}
  const pa = card.prior_art || {}
  return (
    <div className="card-view">
      <div className="card-status-row">
        <span className={`badge badge-${card.status}`}>
          {card.status === 'survivor' ? '存活' : '驳回'}
        </span>
        <span className="mono dim">{card.id}</span>
        <span className="nov-badge" title={NOV_LABELS[pa.novelty_level]}>
          {NOV_BADGE[pa.novelty_level] || '·'} {NOV_LABELS[pa.novelty_level]}
        </span>
      </div>
      <h3 className="card-q">{card.question}</h3>

      <dl className="audit">
        <dt>松开的被夹持自由度</dt>
        <dd>
          <span className="mono">{card.parent_dof}</span>
          {dof && (
            <>
              <span className="lev-tag">{LEVEL_LABELS[dof.leverage_level]}</span>
              <span className="dim">：{dof.statement}</span>
            </>
          )}
        </dd>
        <dt>变形算子</dt>
        <dd>
          {OPERATOR_LABELS[card.operator?.type] || card.operator?.type}
          {card.operator?.stimulus && (
            <span className="dim">（刺激：{card.operator.stimulus}）</span>
          )}
          {card.operator?.note && <div className="dim">{card.operator.note}</div>}
        </dd>
      </dl>

      <FloorBlock floor={card.floor} />

      <dl className="audit">
        <dt>价值画像</dt>
        <dd>
          <span className="kv">商业行动性 <b>{VP_LEVEL[vp.actionable_commercial]}</b></span>
          <span className="kv">概念深度 <b>{VP_LEVEL[vp.conceptual_depth]}</b></span>
          <span className="kv">可落地 <b>{DELIV_LABELS[vp.deliverability]}</b></span>
        </dd>
        {vp.valuable_to_whom && (<><dt>对谁有价值</dt><dd>{vp.valuable_to_whom}</dd></>)}
        <dt>先验技艺</dt>
        <dd>
          {pa.known_name
            ? <span>近似已知：<b>{pa.known_name}</b></span>
            : <span className="dim">未检索到直接同名工作</span>}
          {pa.novelty_watermark && (
            <div className="dim">新颖水印：{pa.novelty_watermark}</div>
          )}
        </dd>
        {Array.isArray(card.lineage) && card.lineage.length > 0 && (
          <>
            <dt>谱系</dt>
            <dd className="mono dim">{card.lineage.join(' → ')}</dd>
          </>
        )}
      </dl>
    </div>
  )
}

function Panel({ cardId, cardsById, dofs, rejected }) {
  if (!cardId) {
    return (
      <div className="panel empty-panel">
        <p>点选地图上的一个点，查看该研究方向的完整推导链：</p>
        <p className="dim">松开了哪条被夹持的自由度 · 用了什么算子 · 是否过证伪闸门 ·
          价值画像 · 先验技艺。</p>
        {rejected.length > 0 && (
          <div className="rejected-list">
            <h4>未过闸门 / 已驳回（{rejected.length}）</h4>
            {rejected.map((c) => (
              <button key={c.id} className="reject-chip"
                      onClick={() => null} title={c.floor?.reject_reason || ''}>
                {c.id}
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }
  return (
    <div className="panel">
      <CardView card={cardsById[cardId]} dofs={dofs} />
    </div>
  )
}

export default function App() {
  const [runs, setRuns] = useState([])
  const [run, setRun] = useState(null)
  const [graph, setGraph] = useState(null)
  const [cards, setCards] = useState([])
  const [map, setMap] = useState(null)
  const [runMeta, setRunMeta] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getJSON('/api/runs')
      .then((rs) => { setRuns(rs); if (rs.length) setRun(rs[0]) })
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!run) return
    setSelected(null)
    Promise.all([
      getJSON(`/api/runs/${run}/graph`),
      getJSON(`/api/runs/${run}/cards`),
      getJSON(`/api/runs/${run}/map`),
      getJSON(`/api/runs/${run}/run`),
    ])
      .then(([g, cs, m, rm]) => { setGraph(g); setCards(cs); setMap(m); setRunMeta(rm) })
      .catch((e) => setError(String(e)))
  }, [run])

  const cardsById = useMemo(
    () => Object.fromEntries(cards.map((c) => [c.id, c])), [cards])
  const rejectedCards = useMemo(
    () => (map?.rejected || []).map((id) => cardsById[id]).filter(Boolean),
    [map, cardsById])

  if (error) {
    return (
      <div className="app">
        <div className="panel empty-panel">
          <p>无法连接引擎 API：{error}</p>
          <p className="dim">先在仓库根目录运行 <code>python -m engine.cli serve</code>。</p>
        </div>
      </div>
    )
  }
  if (!map || !graph || !runMeta) {
    return <div className="app"><p className="dim loading">读取价值地图中…</p></div>
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-name">frameshift</span>
          <span className="brand-sub">问题空间 · 价值地图</span>
        </div>
        <select value={run || ''} onChange={(e) => setRun(e.target.value)}>
          {runs.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <div className="chips">
          <MetricChip label="存活方向" value={runMeta.n_survivors} />
          <MetricChip label="驳回" value={runMeta.n_rejected} />
          <MetricChip label="松开的自由度" value={runMeta.n_dofs} />
        </div>
      </header>

      <p className="paper-line">
        <span className="dim">输入论文：</span>{graph.paper?.title}
        {graph.paper?.arxiv && <span className="mono dim"> · {graph.paper.arxiv}</span>}
      </p>
      <p className="paper-line dim">
        原问题：{graph.original_question?.text}
      </p>
      {graph.dominant_idea && (
        <p className="paper-line dominant">
          <span className="dim">主导观念：</span>{graph.dominant_idea}
        </p>
      )}

      <main className="main">
        <ValueMap map={map} cardsById={cardsById}
                  selected={selected} onSelect={setSelected} />
        <Panel cardId={selected} cardsById={cardsById}
               dofs={graph.clamped_dofs || []} rejected={rejectedCards} />
      </main>
    </div>
  )
}
