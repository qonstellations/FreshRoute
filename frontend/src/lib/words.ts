// Display wording only (ARCHITECTURE §16): plain names for engine ids and short explanations of terms.
// No numbers, no maths: every value shown next to these words is still a served field.

const named = (map: Record<string, string>) => (id: string) => map[id] ?? id

export const policyName = named({
  milp: 'FreshRoute (optimised)',
  milp_markdown: 'FreshRoute + discounts',
  fefo: 'Expiry-first rule (FEFO)',
  fifo: 'Arrival-order rule (FIFO)',
  last_day_50: 'FIFO + 50% off on the last day',
})

export const reasonText = named({
  SHELF_LIFE: 'Would spoil before it sells',
  WINDOW: 'Misses the market’s opening hours',
  CAPACITY_BOUND: 'Truck or market is full',
  DEMAND_CAP: 'Market already has enough',
  LOWER_MARGIN: 'Earns less per kg',
})

export const modeName = named({ ambient: 'normal truck', reefer: 'refrigerated truck', rail: 'train' })

/** Market id → display name ("KR Market mandi, Bengaluru" → "KR Market mandi"); unknown ids stay as they are. */
export type Names = Record<string, string>
export const placeName = (names: Names | undefined, id: string) => names?.[id] ?? id

export const ruleText = named({
  UNKNOWN_ID: 'Plan names a batch, truck or market that does not exist',
  NEGATIVE_QTY: 'Ships zero or negative kg',
  NOT_AVAILABLE: 'Ships a batch before it has arrived at the hub',
  VEHICLE_AVAILABILITY: 'Uses a truck before it is free',
  MODE_MISMATCH: 'Truck type does not match the route type',
  NO_LANE: 'Uses a road that does not exist',
  RAIL_SLOT: 'Train leaves outside its timetable',
  SHELF_LIFE: 'Produce arrives with too little shelf life left to sell',
  DELIVERY_WINDOW: 'Arrives outside the market’s receiving hours',
  STOCK_OVERDRAW: 'Ships more than the batch holds',
  VEHICLE_CAPACITY: 'Overloads a truck',
  VEHICLE_TRIPS_PER_DAY: 'Sends a truck on too many trips in a day',
  RECEIVING_CAPACITY: 'Delivers more than a market can unload in a day',
  DISCOUNT_CAP: 'Discount deeper than allowed',
  DISCOUNT_BELOW_SALVAGE: 'Discount pushes the price below scrap value',
  DISCOUNT_NOT_MONOTONE: 'Discount goes down again after going up',
  DEMAND_CAP_EXCEEDED: 'Sends more than the market is expected to buy (warning only)',
})

export const scenarioName = (s: string) =>
  ({ practice: 'Practice scenario · 200 batches · 8 markets · 8 trucks' } as Record<string, string>)[s.split(/[\\/]/).pop() ?? s]
  ?? s.split(/[\\/]/).pop() ?? s

/** Short explanations shown in <Explain> hover notes. Adapted from docs/GLOSSARY.md. */
/** Where the spoiled food went (Metrics.spoilage_breakdown_kg keys): label, plain explanation, bar colour. */
export const SPOIL_PARTS = {
  handling_loss: { label: 'Lost in handling', color: 'orange',
    note: 'A small share of every delivery is lost while loading and unloading, so this grows with the kg delivered.' },
  delivered_unsold_expired: { label: 'Delivered, never sold', color: 'red',
    note: 'Reached a market but was not sold before it went bad.' },
  origin_expired: { label: 'Never left the farm', color: 'grape',
    note: 'Not shipped at all and went bad where it was harvested.' },
} as const

export const TERM = {
  net: 'Profit after every cost: sales minus the cost of the produce, transport, handling and spoiled stock.',
  spoilage: 'Kilograms that went bad before they could be sold.',
  fulfilment: 'Share of what markets wanted to buy that actually reached them.',
  minFill: 'The share of demand met at the worst-served market. Higher means no market is left short.',
  violations: 'Times the plan broke a hard rule (overloaded truck, rotten on arrival, …). Checked by an independent program.',
  slack: 'Hours of selling life left after the produce arrives, beyond the minimum a market needs. Under 6 h is urgent.',
  shelfLife: 'How many hours a batch can still be sold before it goes bad.',
  q10: 'A standard food-science rule: every 10 °C warmer roughly doubles how fast produce spoils. That is why hot trucks matter.',
  fifo: 'First in, first out: ship stock in the order it arrived, ignoring how fresh it is.',
  fefo: 'First expired, first out: ship the stock closest to going bad first. A strong, common warehouse rule and our main baseline.',
  milp: 'Mathematical optimisation (mixed-integer linear programming). It weighs every truck, market and batch together to find the most profitable plan that breaks no rule.',
  highs: 'HiGHS is a free, open-source optimisation solver. It does the search; FreshRoute builds the problem for it.',
  simulator: 'One shared program replays every plan through the same simulated days and scores it. No plan scores itself.',
  validator: 'A separate program that re-does the maths from scratch and checks every plan against every hard rule.',
  seed: 'The random seed fixes every random draw, so the same seed always gives exactly the same result.',
  frozen: 'Shipments already on the road when the event happens. They can’t be changed, so the re-plan works around them.',
  future: 'One possible version of the next few days, with demand, travel times and shelf life drawn at random. Both plans face the same futures.',
  bands: 'P10–P90: in 8 of 10 futures the result falls inside this bar. The tick (P50) is the middle result.',
  sensitivity: 'We change one assumption at a time and re-run the plan to see how much the result moves.',
  elasticity: 'How much more people buy when the price drops. It is an estimate, so we test it.',
  mipGap: 'How far the plan could be, at most, from the best possible plan. 0% means it is proven best.',
  fallback: 'If the solver ever fails, FreshRoute ships a safe expiry-first plan instead of crashing.',
  manifest: 'A record of everything needed to reproduce this exact result: inputs, settings, code version and package versions.',
  markdown: 'A price cut that helps old stock sell before it spoils.',
  newsvendor: 'Ship a little more or less than the forecast, depending on which costs more: running out or having leftovers.',
  mandi: 'A wholesale produce market, where distributors sell to traders and retailers.',
  reefer: 'A refrigerated truck. Produce lasts much longer in one.',
  synthetic: 'Realistic made-up data built from public sources, not real company records.',
} as const

export type Term = keyof typeof TERM
