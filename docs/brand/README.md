# Brand

Status: alpha. See [`decisions.md`](decisions.md) for what was chosen and why.

## Variants

| File | Use |
|---|---|
| `assets/logo.svg` | Horizontal lockup on light backgrounds. |
| `assets/logo-dark.svg` | Horizontal lockup on dark backgrounds. |
| `assets/icon.svg` | Badge only, light. Avatars, favicons, app icons. |
| `assets/icon-dark.svg` | Badge only, dark. |

All four have transparent backgrounds. The README hero switches between light and dark using a `<picture>` element.

## Colour tokens

| Token | Light | Dark | Role |
|---|---|---|---|
| `ink` | `#0F172A` | `#E2E8F0` | Target, text |
| `accent` | `#F59E0B` | `#F59E0B` | Pike, `PIKE` |
| `tint` | `#F1F5F9` | `#16203A` | Badge fill, cut-outs |

## Usage

- Keep clear space around the lockup equal to the height of the badge's inner chip (about a quarter of the badge).
- Do not recolour the pike; amber is the only accent.
- Do not stretch, rotate, or add effects.
- Below 32px use the icon, not the lockup.

## Changing the logo

The logo is generated. Do not edit the SVGs by hand.

```bash
# 1. edit brand/logo.spec.json (or tools/logo/parts.py for new shapes)
python -m tools.logo build     # regenerate assets/
python -m tools.logo check     # fail if assets differ from the spec (CI runs this)
python -m tools.logo concepts  # regenerate the frozen 50-concept round
```

A new exploration round should be a new function and folder, not a reshuffle of the existing one; `tests/unit/test_logo_tools.py` pins concept numbers and filenames.

| Spec field | Options |
|---|---|
| `mark.target` | `bot`, `rack`, `datacenter`, `chip`, `cyclops`, `promptbot` |
| `mark.pike` | `spear`, `needle`, `lance`, `bolt` |
| `mark.impact` | `cracks`, `ring`, `none` |
| `mark.container` | `none`, `circle`, `square`, `shield` |
| `wordmark.style` | `light-bold`, `caps`, `mono`, `slash` |
