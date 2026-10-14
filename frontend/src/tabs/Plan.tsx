// Plan tab (ARCHITECTURE §15–§16): dispatch table, reason cards, discount cards, shelf-life map.
// Every number is a served field (DATABASE §5.9–§5.10), only rounded for display.
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DispatchRow, DispatchSheet, ReasonCard, ReasonCards, RunDetail } from '../types'

const num = (v: number | null | undefined) =>
  v == null ? '' : v.toLocaleString('en-IN', { maximumFractionDigits: 1 })

// Formatting the served records back into CSV (no endpoint serves dispatch_sheet.csv as a file).
function csvUrl(rows: DispatchSheet['csv']) {
  const cols = Object.keys(rows[0] ?? {})
  const cell = (v: unknown) => {
    const s = v == null ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s
  }
  const body = [cols.join(','), ...rows.map(r => cols.map(c => cell(r[c as keyof typeof r])).join(','))].join('\n')
  return URL.createObjectURL(new Blob([body + '\n'], { type: 'text/csv' }))
}

function Dispatch({ sheet, runId, onRow }:
  { sheet: DispatchSheet; runId: string; onRow: (r: DispatchRow) => void }) {
  const [href, setHref] = useState('')
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    const u = csvUrl(sheet.csv)
    setHref(u)
    return () => URL.revokeObjectURL(u)
  }, [sheet])
  const copy = () => navigator.clipboard.writeText(sheet.text).then(() => {
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  })

  return (
    <section>
      <div className="section-head">
        <h2>Dispatch sheet <span className="caption">{sheet.csv.length} lines, priority order</span></h2>
        <a className="button" href={href} download={`${runId}__dispatch_sheet.csv`}>Download CSV</a>
      </div>
      <div className="scroll">
        <table className="dispatch">
          <thead><tr>
            <th>#</th><th>Vehicle</th><th>Trip</th><th>Depart</th><th>Destination</th><th>Batch</th>
            <th>Commodity</th><th className="n">kg</th><th className="n">Slack h</th><th className="n">Arrive by h</th>
          </tr></thead>
          <tbody>
            {sheet.csv.map(r => (
              <tr key={`${r.trip_id}|${r.batch_id}|${r.priority_rank}`} className="clickable" onClick={() => onRow(r)}
                title="Show reason card">
                <td className="n">{r.priority_rank}</td><td>{r.vehicle_id}</td><td>{r.trip_id}</td>
                <td>{r.depart_clock}</td><td>{r.dest_name}</td><td>{r.batch_id}</td><td>{r.commodity}</td>
                <td className="n">{num(r.kg)}</td><td className="n">{num(r.slack_h)}</td>
                <td className="n">{num(r.arrive_by_h)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="section-head">
        <h3>Driver message</h3>
        <button onClick={copy}>{copied ? 'Copied' : 'Copy text'}</button>
      </div>
      <pre className="whatsapp">{sheet.text}</pre>
    </section>
  )
}

const signed = (v: number) => (v > 0 ? '+' : '') + num(v)

function Drawer({ card, onClose }: { card: ReasonCard | null | undefined; onClose: () => void }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    addEventListener('keydown', esc)
    return () => removeEventListener('keydown', esc)
  }, [onClose])
  if (card === undefined) return null
  const c = card?.chosen
  return (
    <div className="drawer" role="dialog" aria-label="Reason card">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      {!card || !c ? <p className="placeholder">No reason card for this shipment (run written before U-01?).</p> : <>
        <h3>{card.shipment_id} · {card.batch_id} {card.commodity}</h3>
        <p className="card-text">{card.text}</p>
        <h4>Chosen <span className="caption">priority #{card.priority.rank}</span></h4>
        <dl>
          <dt>Destination</dt><dd>{c.dest_id} by {c.vehicle_id} ({c.mode})</dd>
          <dt>Depart → arrive</dt><dd>{num(c.dispatch_h)} h → {num(c.arrival_h)} h</dd>
          <dt>Load</dt><dd>{num(c.kg)} kg</dd>
          <dt>Life at arrival</dt><dd>{num(c.usable_life_at_arrival_h)} h</dd>
          <dt>Slack</dt><dd>{num(c.slack_h)} h</dd>
          <dt>Margin</dt><dd>₹{num(c.margin_inr_kg)}/kg</dd>
        </dl>
        <h4>Runner-up</h4>
        {card.runner_up ? <p>
          {card.runner_up.dest_id} <code>{card.runner_up.reason_code}</code> · chosen − runner-up:{' '}
          margin ₹{signed(card.runner_up.margin_delta_inr_kg)}/kg (₹{signed(card.runner_up.margin_delta_inr)} on this load),
          slack {signed(card.runner_up.slack_delta_h)} h
        </p> : <p className="placeholder">No alternative.</p>}
        {card.discount && <>
          <h4>Discount</h4>
          <p>{num(card.discount.tier_pct)} % off from day {card.discount.day} · risk {card.discount.risk.toFixed(2)}
            {card.discount.capped_by !== 'none' && ` · capped by ${card.discount.capped_by}`}</p>
        </>}
        <h4>Alternatives <span className="caption">deltas = chosen − alternative</span></h4>
        <table>
          <thead><tr><th>Dest</th><th>Mode</th><th className="n">Day</th><th>Reason</th>
            <th className="n">Slack h</th><th className="n">Δ ₹/kg</th><th className="n">Δ slack h</th></tr></thead>
          <tbody>{card.alternatives.map(a => (
            <tr key={`${a.dest_id}|${a.mode}`} className={a.feasible ? '' : 'infeasible'}>
              <td>{a.dest_id}</td><td>{a.mode}</td><td className="n">{a.dispatch_day}</td><td><code>{a.reason_code}</code></td>
              <td className="n">{num(a.slack_h)}</td><td className="n">{signed(a.margin_delta_inr_kg)}</td>
              <td className="n">{signed(a.slack_delta_h)}</td>
            </tr>))}
          </tbody>
        </table>
      </>}
    </div>
  )
}

function DiscountCards({ cards, onOpen }: { cards: ReasonCard[]; onOpen: (c: ReasonCard) => void }) {
  const list = cards.filter(c => c.discount)
  return (
    <section>
      <h2>Discount cards <span className="caption">{list.length} shipments marked down</span></h2>
      {!list.length ? <p className="placeholder">No discounts in this run.</p> : <div className="cards">
        {list.map(c => c.discount && (
          <button key={c.shipment_id} className="discount-card" onClick={() => onOpen(c)}>
            <strong>{num(c.discount.tier_pct)} % off</strong> from day {c.discount.day}
            <span>{c.batch_id} {c.commodity} → {c.chosen.dest_id}</span>
            <span className="caption">unsold-risk {c.discount.risk.toFixed(2)}
              {c.discount.capped_by !== 'none' && ` · capped by ${c.discount.capped_by}`}</span>
          </button>))}
      </div>}
    </section>
  )
}

export function Plan({ runId }: { run: RunDetail; runId: string }) {
  const [sheet, setSheet] = useState<DispatchSheet | null | undefined>(undefined)
  const [cards, setCards] = useState<ReasonCards | undefined>(undefined)
  const [open, setOpen] = useState<ReasonCard | null | undefined>(undefined) // undefined = drawer closed
  const [error, setError] = useState('')
  const close = useCallback(() => setOpen(undefined), [])

  useEffect(() => {
    setSheet(undefined); setCards(undefined); setOpen(undefined); setError('')
    const fail = (what: string) => (e: Error) => setError(`Cannot load ${what}: ${e.message}`)
    api.dispatchSheet(runId).then(setSheet).catch(fail('dispatch sheet'))
    api.reasonCards(runId).then(setCards).catch(fail('reason cards'))
  }, [runId])

  // dispatch rows carry no shipment_id; priority_rank + batch_id identify the plan row (§5.2, §5.10)
  const openRow = (r: DispatchRow) => setOpen(cards?.find(c => c.priority.rank === r.priority_rank && c.batch_id === r.batch_id) ?? null)

  return (
    <div className="plan">
      {error && <p className="banner error">{error}</p>}
      {sheet === undefined ? <p className="placeholder">Loading…</p>
        : sheet ? <Dispatch sheet={sheet} runId={runId} onRow={openRow} />
        : <p className="placeholder">No dispatch sheet for this run.</p>}
      {cards === null && <p className="placeholder">No reason cards for this run.</p>}
      {cards && <DiscountCards cards={cards} onOpen={setOpen} />}
      <Drawer card={open} onClose={close} />
    </div>
  )
}
