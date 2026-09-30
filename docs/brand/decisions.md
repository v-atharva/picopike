# Logo decisions

Status: **alpha, open to revision.** Nothing here is final; this records what was chosen on 2026-09-30, why, and what was left on the table so it can be picked up again.

## Chosen: concept 16

| Axis | Choice | Why |
|---|---|---|
| Target | `chip` (processor with pins) | Reads as "AI hardware / silicon" and suits a model-input classifier better than a generic robot. |
| Pike | `spear`, 22° | Bold enough to survive at 16px; the shallow angle gives a strike direction without looking like an arrow icon. |
| Impact | `cracks` | Three short cut-outs at the tip. Says "it lands" at no extra weight. |
| Flip | yes | The pike enters from the right, so the mark leads the eye into the wordmark. |
| Container | rounded `square` | Makes a ready-made app icon and avatar. |
| Palette | navy `#0F172A` on `#F1F5F9`, amber `#F59E0B` | Two colours only. Amber marks the thing that strikes. |
| Wordmark | caps, `PICO` navy and `PIKE` amber | Two halves mirror the name. Letter-spaced at 1. |

The idea to convey: a very small thing (pico) that hits something much larger and harder (the pike against the chip), like a bee stinging a giant.

## Shortlist kept for later

Concept numbers refer to the frozen exploration round (`assets/logo-concepts/round-2/`).

| # | Why it stayed |
|---|---|
| 04 | Clearest bot-vs-pike story, stacked lockup. |
| 07, 20 | Keep the original shield idea (shield container with a bot or rack). |
| 22 | Best dark-mode icon. |
| 26 | Most distinctive chip icon (bolt trails). |
| 36 | Best avatar and favicon candidate. |
| 44 | Cleanest stacked lockup. |

## Not chosen, on purpose

- **Shield as the main symbol.** Earlier round-1 concepts (`assets/logo-concepts/round-1/`) used a shield; the direction moved to a pike striking a target instead. The shield container remains an option.
- **Pistol or box motifs.** Mentioned once during exploration and not drawn.
- **Live text in the wordmark.** It is still live text that falls back to system fonts. Convert to outlines before any public launch.

## Where things live

| What | Where |
|---|---|
| Design as data | `brand/logo.spec.json` |
| Generator | `tools/logo/` (`parts`, `render`, `concepts`, `cli`) |
| Generated logos | `assets/logo*.svg`, `assets/icon*.svg` (do not hand-edit) |
| Exploration archive | `assets/logo-concepts/` |
| Private gallery of all 50 | <https://claude.ai/artifact/7SSGmXER99Kr1saRnkFEXf> (owner-only; share from the page's Share menu) |

## Open items

- [ ] Figma: authenticate the Figma connector (`/mcp`, then "claude.ai Figma") and create a Figma file from the chosen SVGs so the design can be refined visually. Until then the SVGs are importable into Figma by drag and drop.
- [ ] Outline the wordmark text.
- [ ] Add a favicon export and a social preview image (1280x640).
- [ ] Decide whether to keep the shield as a secondary container variant.
