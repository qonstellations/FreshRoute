# Brag Plan: FreshRoute

## What is this app?
Decision support for perishable produce: each morning it picks which batch goes to which market on which truck, then an independent simulator and validator measure the plan. All data is synthetic.

## The angle
A morning in twenty seconds, told through the working console: the route board, the driver message, the measured result. Every number is read from `outputs/demo_backup/practice__*__s42` and labelled synthetic.

## Hook (0-3.5s)
"This spinach has 5 hours to spare." then "Which truck goes first?" (Hoskote spinach, 5.2 h slack in the stored plan.)

## Key moments
- Route board: two hubs on the left, 8 markets on the right, most urgent first, each with kg and hours-to-spare pills, lanes drawn between them.
- Dispatch: "19 trips. 233 shipments." plus two real driver-message cards (WhatsApp-ready text).
- Result: FEFO net 271,027 vs FreshRoute 404,432; +133,405; spoilage 904 to 736 kg; 0 rules broken.

## Outro / punchline
FRESHROUTE. "Fresh produce. Smarter dispatch." Footer: synthetic practice scenario, seed 42.

## User flow worth showing
Entry: the plan lands on Today's plan. Key action: read the route board, open the loading list. Result: paste the driver message, check the scoreboard.

## Tone
- Preset: default
- Creative direction: a calm product demo that opens on one anxious spinach crate
- Interpretation: clean cuts, readable holds, no jokes beyond the hook.

## Format: landscape, 1920x1080
## Duration: 21.5s

## Visual identity (from the project)
- Background: #fef0d5 (cream), #0f1e16 (dark green scenes)
- Accent: #1f7a4d / #4fbf7f; alert #a8201a
- Text: #174229 on cream, #fef0d5 on dark
- Display font: Anton; body Inter; mono Kode Mono
- Strongest visual element: the route board (hub cards, market cards, slack pills, lanes)

## Share copy (draft)
FreshRoute decides which produce goes on which truck, then proves it: +₹133k net vs the expiry-first baseline, 0 rule violations. Synthetic data, measured numbers.

## Audio direction
- Role: warm bed with sparse accents
- Music: happy-beats-business-moves-vol-1 (120 BPM), fade-out under the outro
- Music cue guidance: preset read. Strong cues 18.02s (name slam). Beat grid 4.52-6.02 for the market-card pairs, 10.52/11.52 for driver cards.
- Audio-reactive treatment: none (extraction helper unavailable; documented)
- SFX posture: sparse, motion-matched
- Restraint rule: no stacking of hits over text reads

## Storyboard

### Scene 1 — Hook — 3.5s
Two slams: "This spinach has 5 hours to spare." (0.3-1.9), "Which truck goes first?" (2.0-3.5).
Sequential/interaction: none
Audio intent: low impact on each line
Transition mood: hard cut → Scene 2

### Scene 2 — Route board — 6.5s
Title "8 markets. Most urgent first." Hub cards slide in, market cards pair in on beats (4.52, 5.02, 5.52, 6.02), lanes draw, hold to 10.0.
Sequential/interaction: yes — 8 cards in 4 pairs, then full hold of 3.5s
Audio intent: soft chip taps per pair
Transition mood: clean → Scene 3

### Scene 3 — Driver messages — 4.0s
"19 trips. 233 shipments." Two driver cards slide in at 10.52 and 11.52, hold to 14.0.
Sequential/interaction: yes — 2 cards one by one
Audio intent: bong on the first card
Transition mood: clean → Scene 4

### Scene 4 — Result — 4.0s
FEFO bar to ₹271,027, FreshRoute bar to ₹404,432, then "+₹133,405 · spoilage 904 → 736 kg · 0 rules broken".
Sequential/interaction: yes — two counters, then summary line
Audio intent: quiet
Transition mood: hard cut → Scene 5

### Scene 5 — Outro — 3.5s
Name slams at 18.02 (strong cue), tagline, synthetic footer.
Sequential/interaction: none
Audio intent: bell hit on the name
Transition mood: end

**Music mood for this video:** upbeat, light
**Audio summary:** bed from 0, small taps on cards, one bell on the name, fade out at the end.
