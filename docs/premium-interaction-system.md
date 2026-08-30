# Premium interaction system

Pauli's Place borrows behavior from Emil Kowalski's design-engineering work rather than treating polish as decoration.

## Chosen patterns

### Apple design skill
Used as the interaction standard:
- immediate pointer-down/press feedback
- interruptible spring motion instead of decorative fixed-duration animation
- spatially consistent sheets and overlays
- translucent material hierarchy for floating chrome
- typography and spacing that prioritize hierarchy over density
- reduced-motion, reduced-transparency, and increased-contrast fallbacks

### Sonner interaction model
Borrowed for lifecycle feedback rather than adding another permanent dashboard region. Mission creation, approval decisions, sign-in requests, and failures surface as compact non-blocking notices that transition from pending to verified success/failure. The notice never substitutes for canonical persisted state.

The project does not currently add Sonner as a dependency because the required behavior is small and the existing Framer Motion runtime can deliver the same interaction contract without adding another package to the production surface.

### Vaul interaction model
Borrowed for agent detail: bottom-sheet hierarchy on mobile, direct drag tracking, velocity-aware dismissal, background focus, and an interruptible spring. On wider screens the same information becomes a side sheet.

Vaul itself is not installed because its upstream repository currently marks the project unmaintained. Keeping the behavior on the already-installed Framer Motion stack avoids making an unmaintained package foundational while retaining the useful interaction design.

## Agent-control rules

- A row is directly inspectable; it responds immediately to press/tap.
- Detail shows only recorded fields: current status, role/specialty, heartbeat, and world location.
- Controls that do not exist in Mission Control are not fabricated in the UI.
- The sheet links to the full workforce control surface for deeper operations.
- Runtime success remains evidence-driven; notifications are feedback, not completion receipts.

## Reuse across Pauli control applications

Use this system for dashboards, agent portals, mobile control centers, and business-owner surfaces:

1. primary screen = outcome and next decision
2. toast/notice = immediate local feedback
3. sheet/drawer = contextual inspection without navigation loss
4. full route = technical drill-down
5. modal = only truly blocking/irreversible decisions

This keeps the interface shallow for owners while preserving deep control for operators.
