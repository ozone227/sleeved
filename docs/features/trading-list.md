# Sleeved Feature: Trading List

Oct 23, 2026 · @Ryan Bond

Depends on [`docs/multi-user-architecture-plan.md`](../multi-user-architecture-plan.md)
for per-user keep targets and check-off state — not yet implemented.

## Summary

Sleeved should compare a player's inventory against the full card list for a game and show two things: the copies still needed to reach a keep target, and the copies held beyond it that can be traded. Today the gallery only shows what is owned, so finding gaps means a manual count.

A working prototype, the Night City Trading List, was built by hand on 23 Oct 2026 from the Drive inventory (945 cards) and the community card database (151 Cyberpunk TCG cards). It found 157 copies needed across 66 cards and 153 spare copies across 66 cards. This spec turns that prototype into a gallery feature.

## Goals and non-goals

**Goals**

- Show every card in a game's card list that is below its keep target, with how many copies are needed.
- Show every card above its keep target, with how many spare copies there are.
- Let the owner set keep targets per card type, so Legends can differ from other cards.
- Treat rare variants (Iconic, alternate-art) as their own collecting goal: own at least one of each, regardless of how the numeric keep target nets out.
- Work from the existing per-game card data, with no manual counting.
- Produce a list that can be shared by link for trades.

**Non-goals for the first version**

- Prices, market values or links to stores.
- Matching trades between two collections (see `multi-user-architecture-plan.md` — this becomes a natural follow-up once inventories are per-user rows in a database, not a file each).
- Changing the owner's inventory from the trading list. Ticking a card off is a reminder, not an inventory edit.

## User stories

1. As a collector, I want to set how many copies of each card I keep, so the list matches how I play and collect.
2. As a collector, I want to see every card I'm short on and by how many, so I know what to buy or trade for.
3. As a collector, I want to see cards I don't own at all, including promos and starter-deck cards, so nothing is missed.
4. As a collector, I want to see which alt-art or Iconic variants I'm missing even if I already have enough copies of the card overall, so I don't lose track of the ones I actually want for the art.
5. As a trader, I want to see my spare copies, so I know what I can offer.
6. As a trader, I want to filter both lists by color and type, so I can put a trade together quickly.
7. As a collector, I want to tick off cards as I get them at an event, before I update my inventory, and have that stick when I check from another device later.
8. As a trader, I want to send someone a link to my list, so they can see what I need and what I have.

## Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| TL-1 | Load the game's full card list as well as the owner's inventory, so cards with 0 copies show up. | Must |
| TL-2 | Keep targets are set per card type in the game config. Cyberpunk TCG defaults: Legends 3 (2 to play, 1 to keep); Units, Gear and Programs 7 (two 3-copy playsets, 1 to keep). | Must |
| TL-3 | Allow a per-card override of the target (for example, keep 1 of a promo). | Should |
| TL-4 | Owned count = the sum of copies across every printing of the same card, matched by a stable card ID (not by name). | Must |
| TL-5 | Needed section: cards where owned is below target, showing owned, target and need. | Must |
| TL-6 | Extras section: cards where owned is above target, showing owned and spare. | Must |
| TL-7 | Variant-gap check: for any card with a known Iconic or alternate-art printing, flag it separately if that specific printing is owned zero times — independent of whether the card's aggregate owned count already meets target. | Must |
| TL-8 | Summary row: total copies needed, cards short, total spare copies, copies needed by color, and count of missing rare variants. | Must |
| TL-9 | Group both sections by color in the game's color order, then by type, then by name. | Must |
| TL-10 | Filters for color and type apply to both sections at once. | Must |
| TL-11 | Each needed card shows its rarity, source (booster, starter deck, promo) and collector number. | Should |
| TL-12 | A checkbox per needed card marks it as acquired. Persisted per account (see `multi-user-architecture-plan.md`), so it survives a reload and follows the owner across devices; it never changes the inventory itself. | Should |
| TL-13 | The list has its own shareable link and renders without requiring the viewer to be signed in, same as the gallery. | Must |
| TL-14 | Show the inventory date the list was built from. | Should |
| TL-15 | Works at phone width, for use at events. | Must |

## Data model and calculation rules

The feature needs one new reference file per game, one schema change, and relies on the accounts/database work in `multi-user-architecture-plan.md` for the per-user pieces.

| File / store | Change |
| --- | --- |
| `games/{game-id}.cards.json` (new, versioned in git, not object storage) | The full card list for the game: stable numeric/string `cardId`, canonical name, color, type, rarity, set or source, collector number, and a flag per known alt-art/Iconic printing. https://cyberpunktcg.com/cards is the official source of truth for this data — treat it as the reference to verify against. It has no public/bulk API (confirmed Oct 2026), so initial generation still starts from the community database (jclopes/tcg\_scanner, 151 cards) and gets manually checked against the official site rather than pulled from it directly. Lives in git, not the object store, because it's shared reference data identical for every user — reviewable by PR the same way adding a game is today. |
| `games/cyberpunk-tcg.json` | Add `keepTargets`, e.g. `{"Legend": 3, "default": 7}`, plus an optional `overrides` map by `cardId`. |
| Inventory data | Each owned-copy entry carries `cardId` (foreign key into `games/{game-id}.cards.json`), not a name string. Once `multi-user-architecture-plan.md` lands, this is an `inventory_entries` row in Postgres rather than a field in a JSON file; `schema/inventory.schema.json`'s current 1–3 cap on `copies` also needs raising — the real inventory has up to 12 of a card. |

Calculation, per card in the catalog:

```
owned  = sum of copies for every inventory entry with this card's cardId (all printings)
target = overrides[cardId] ?? keepTargets[card.type] ?? keepTargets.default
need   = max(0, target - owned)
spare  = max(0, owned - target)

for each known variant printing (Iconic, alt-art) of a card:
  variantOwned = sum of copies for inventory entries with that printing's cardId
  if variantOwned == 0: flag as a missing variant, regardless of need/spare above
```

Matching by `cardId` instead of name removes the fuzzy-matching risk the
original draft had (hand-typed names vs. a community database never agreeing
on punctuation). An inventory entry with a `cardId` that isn't in the
catalog should be flagged, not dropped.

## Acceptance criteria

Run against the 23 Oct 2026 inventory (945 copies, 155 entries) and default targets, the feature must match the prototype's totals (the prototype matched by name; re-verify these once `cardId` matching is in place, since it may surface entries the name-matching prototype missed or double-counted):

| Check | Expected |
| --- | --- |
| Total copies needed | 157 across 66 cards (41 Legend copies, 116 others) |
| Total spare copies | 153 across 66 cards; no Legends |
| Cards exactly at target | 19 (17 non-Legend, plus V: Streetkid and Kerry Eurodyne: Axe, Attitude, Audience at 3) |
| Cards with 0 owned | Johnny Silverhand: Rocking Renegade and Rebecca: Having a Moment (promo), need 3 each |
| Variant merge | Kerry Eurodyne: Axe, Attitude, Audience = 2 standard + 1 Iconic = 3 owned, need 0, and the Iconic printing's own `cardId` shows 1 owned so it is not flagged as a missing variant |
| Largest spares | +5 each: Arasaka Emergency Radioport, Mantis Blades, Kiroshi Optics, Mandibular Upgrade, Evelyn Parker: Scheming Siren, Floor It |
| Filters | Color = Blue, Type = Program shows Nocturne OP55 N1, Pyramid Song, Towerfall under needed, and six Programs under extras |
| Check-offs | Ticking a card removes its copies from the summary totals and is still ticked when the owner reloads from a different device |

- [ ] Changing the Legend target to 7 raises total needed to 265 copies.
- [ ] Adding a card to the owner's inventory updates both sections on the next load, with no rebuild.
- [ ] A card with an owned Iconic/alt-art printing but a different `cardId` per printing correctly contributes to the aggregate `owned` count for the base card AND is correctly cleared from the missing-variant list.

## Open questions and future work

- [ ] Where does `games/{game-id}.cards.json` come from for future games, and who refreshes it when a new set releases?
- [ ] Should the shared link hide the extras section, the needed section, or neither?
- [ ] Should a ticked card offer a one-step inventory update, or stay a reminder only?

Later: export the list as CSV, show market prices beside needed cards, and match one collector's extras against another's needs (a natural follow-up once inventories are per-user database rows rather than files — see `multi-user-architecture-plan.md`).
