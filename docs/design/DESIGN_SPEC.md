# DESIGN_SPEC.md: Requirements distilled from the approved mockups

Source: the "EMI Copilot – UI Mockups" design canvas. The reference markup is copied into `docs/design/mockups-source/` (`C1`–`C10` customer screens, `M1`–`M8` merchant screens, `Components`, `Main` style sheet, `CustomerStates`, `MerchantStates`, `TamilScreens`, `canvas.json`).

**How to use the mockup sources:** they are Design Component pages (`*.dc.html`) and will not render on their own. Use them as a reference for layout, spacing, states and for the **English and Tamil string tables** inside each file's script block. When this spec and a mockup disagree, stop and ask.

## 1. Design principles

- Customer: one main action per screen; language toggle (EN / தமிழ்) on every screen; plain words.
- Merchant: two tabs in shop language, **New EMI sale** and **Sales report**. Everything else opens in place as an expandable card on the report, never as a separate page.
- Every number the AI says is also on screen. Voice is optional.
- No interest rates, no card fields, no "best for you", no urgency.
- Sample data is not labelled on screen; it is recorded below.

## 2. Tokens

| Token | Value | Use |
|---|---|---|
| Navy | `#002E6E` | Headers, accents |
| Deep navy | `#0B1F3A` | Body text |
| Cyan | `#00BAF2` | Primary buttons (labels are navy, never white) |
| Orange | `#F5A524` | Voice, Stretching |
| Green | `#12B886` | Comfortable, ₹0 |
| Red | `#E5484D` | Risky, warnings |
| Light blue | `#EEF6FB` | Page and soft cards |
| Slate | `#5B6B82` | Secondary text |
| White | `#FFFFFF` | Cards |
| Green text on tint | `#0A6E50` on `#E3F7F0` | Comfortable label |
| Orange text on tint | `#8A5300` on `#FEF3DC` | Stretching label |
| Red text on tint | `#B4232A` on `#FDE8E8` | Risky label |

Type: Inter (English) and Noto Sans Tamil in one stack; tabular numerals for money. Money 32/700, Title 22/700, Body 16/400, Label 14/600. Cards radius 16 with soft shadow; inputs and chips radius 12 with 1px `#DCE7F0`. Spacing scale 4, 8, 12, 16, 24, 32. Touch targets 48 px minimum, 56 px primary. Indian digit grouping (₹1,84,000).

Viewports: customer 360 x 800, merchant tablet 1024 x 768, merchant phone 360 x 800.

## 3. Comfort bands

Exactly three, each with icon and word (never colour alone): **Comfortable** (below 35%), **Stretching** (35% to 50%), **Risky** (above 50%). Thresholds are demo heuristics held in one configuration class.

## 4. Sample data (one consistent data set)

| Item | Value |
|---|---|
| Shop | "Ravi Electronics", Shop ID `RAVI-0193`, "Counter tablet 1" |
| Product | Example phone, 128 GB, ₹22,000 (other catalogue items and prices exist in M2) |
| Plan A | No-cost EMI, 6 months, ₹3,667 a month, ₹0 extra, total ₹22,000, funded by Brand |
| Plan B | Card EMI, 6 months, ₹3,850 a month, ₹1,100 extra, total ₹23,100 |
| Plan C | Cardless credit, 12 months, ₹2,050 a month, ₹2,600 extra, total ₹24,600 |
| Customer context (synthetic) | Inflow ₹30,000 a month, existing EMIs ₹8,000 (27%) |
| Comfort ratios | A 38.9%, B 39.5%, C 33.5% |
| Risky example | Second synthetic customer, inflow ₹20,000, ratio 59.3% |
| Budget | ₹3,000 (misheard value ₹30,000); "no plan fits" state uses ₹1,800 |
| Alternatives | ₹4,000 down payment gives ₹2,999 a month, 36.6%; cheaper 64 GB model at ₹18,000 gives ₹3,000 a month, 36.7% |
| Receipt | Phone ending 42, 6-digit OTP, reference `EMI-2611-0042`; cooling-off wording is a placeholder for the lender's real period |
| Session | QR code number 4821 |
| Funnel (7 days) | 120 started, 96 budget, 88 viewed plans, 51 consented, 44 paid; biggest drop: 37 left after seeing plans |
| Budget buckets | 5, 7, 14, 21, 49 customers (96 total); 12 wanted under ₹3,000 with nothing extra |
| Money due from brands | ₹1,84,000 in three batches: ₹72,000 on 13 Jan, ₹64,000 on 28 Jan, ₹48,000 on 12 Feb 2027 |

## 5. Customer screens (phone, opened by QR)

| ID | Screen | Content | States |
|---|---|---|---|
| C1 | Welcome and language | Shop name, product and price, language choice (Tamil / English), one line on data use, Start | default |
| C2 | Budget | Large ₹ input per month, microphone, confirm line ("You said ₹3,000. Correct?"), edit | empty, typed, voice captured, misheard (fix or try again) |
| C3 | Comfort check consent | Why, what is read (two items), "the shop cannot see this", "advice, not a credit decision", Allow and Skip, skip note | default |
| C4 | Options comparison | Plan cards: name, tenure, "Each month ₹X for N months", "Extra in total ₹Y on top of the price", band chip, total, Details, Choose; sort note; trade-off note | loaded, loading, no-fit (shows all plans, "above your budget") |
| C5 | Comfort detail | Plan header, band, two explanation lines, bar with marks at 0, 35, 50, 100%, "current EMIs" vs "this plan", inflow, "how we worked it out", guidance | per band |
| C6 | Smarter alternatives | Your plan, chips (down payment, longer tenure, cheaper model), recomputed monthly, "was ₹3,667", extra, band and ratio | default, selected, nothing-better |
| C7 | Explanation | Plain text (Tamil or English), play audio with time, two highlighted numbers, "AI wrote this" note, fallback text, plan recap, teach-back entry, continue | text only, audio playing, AI unavailable |
| C8 | Teach-back (optional) | Chosen plan, prompt to say terms in own words, mic, close-enough feedback ("₹3,667 × 6", "₹0 extra"), try again, continue, skip | default, close, again |
| C9 | Consent and OTP | Plan summary (monthly, extra, tenure, total), 6-digit OTP, resend timer, cooling-off note, agree line, Confirm | default, wrong OTP, expired |
| C10 | Handoff and receipt | Title and body per state, plan recap, reference number, cooling-off note, Continue on Paytm | handoff, confirmed, pending, failed |

Happy path: C1, C2, C3, C4, C6, C7, C9, C10. C5 opens from C4 details; C8 is optional between C7 and C9.

## 6. Merchant screens (tablet-first; phone variants for M3 and M8)

| ID | Screen | Content | States |
|---|---|---|---|
| M1 | Sign-in and pairing | Shop ID, pairing PIN, Pair device; note "No PIN? Ask the shop owner to create one in the owner app" | default, wrong PIN |
| M2 | New EMI sale (counter list) | Search products, product list with offer summary and price, price at counter, "Show QR to customer"; "At the counter now" list with customer count, product, code, status, action | empty, product chosen |
| M3 | Show QR to customer | QR, product and code, "Opens on their phone. No app needed.", status chip, chosen plan once agreed, "Take payment", back to list | choosing, ready to pay |
| M4 | Handoff and status | Chosen plan table (plan, product, price, monthly, funded by), EDC steps (choose Brand EMI, pick product and tenure, check amount), "No EDC at hand? Send payment link", payment status | waiting, paid, failed |
| M5 | Sales report | Range (Today, This week, This month), weekly message with EN / தமிழ் toggle and sent state, funnel with biggest drop, expandable cards: **Missed sales** (insight, suggested action, share with brand rep, budget buckets), **Money due from brands** (batches, estimated dates, status), "What you can do to sell more" | loaded, empty ("No EMI sales this week yet" with New EMI sale) |
| M8 | Weekly message (phone) | The AI-written message in the shop's language | default |

The merchant sees only `CHOOSING` or `READY_TO_PAY` per customer while the customer decides, then the merchant-side outcome `PAID`, `PAYMENT_NOT_COMPLETED` or `EXPIRED`; plus the chosen plan and totals. Never income, EMIs, ratios or step-by-step progress (the M3 "Not scanned yet" state is not built). Report counts from 1 to 4 show as "fewer than 5".

## 7. Behaviours implied by the mockups that the code must honour

1. Plan cards always show monthly and extra-in-total at the same size.
2. "No plan fits" still lists every plan, labelled "above your budget".
3. Skipping the comfort check is allowed; plans then show without bands.
4. Wrong or expired OTP shows a calm message and offers resend; no lockout wording that blames the customer.
5. Failed or pending payment never says "declined"; it explains the next step.
6. If AI is unavailable the explanation screen shows the standard text with no error banner and no missing numbers.
7. The merchant list shows "Ready to pay" only after the customer consents.
8. Language choice carries from C1 across every screen and into the receipt.

## 8. Open questions raised by the design (must be answered, see the implementation plan)

- M1 refers to an "owner app" that creates pairing PINs, which is not part of the design. How are PINs created for the demo?
- M5 has "Share with brand rep". What does it do in the demo?
- M5 has a weekly message with a "sent" state. Is sending real (for example WhatsApp or SMS) or simulated?
- The cooling-off period wording is a placeholder.
