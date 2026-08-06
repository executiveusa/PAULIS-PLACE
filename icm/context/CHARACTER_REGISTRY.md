# CHARACTER REGISTRY — Paulie's Place (Seattle 2056)

> File: `icm/context/CHARACTER_REGISTRY.md`

The Yappyverse lounge population. Each avatar is the face of a real agent role inside PAULIS-PLACE. Each row maps to a worker + voice + 3D model handle.

| avatar_id | name | role | worker_profile | voice_provider | model_handle | accent |
|---|---|---|---|---|---|---|
| av_paulie | Paulie "The Plaque" Fontaine | Boss, lounge owner, signs Council approvals | judge | eleven_tts `sk_255591...` | glb/paulie.glb | Italian-American, slow, gravely |
| av_zia | Zia "Numbers" Navarro | CFO, runs the books, RECONCILER worker | score | eleven_tts `Rachel` | glb/zia.glb | Mexican-American, fast, clipped |
| av_marco | Marco "Trender" Lee | Trend Scorer, front-of-house | score | eleven_tts `Brian` | glb/marco.glb | Korean-American, energetic |
| av_dex | Dex "Words" Holloway | Designer + Zernio copywriter | write_short | eleven_tts `Adam` | glb/dex.glb | Pacific Northwest, dry |
| av_sasha | Sasha "Pixels" Ortiz | 3D scene director + social post art | implement | eleven_tts `Nicole` | glb/sasha.glb | Cuban-American, warm |
| av_wren | Wren "The Vault" Yamasaki | Ledger keeper + secret auditor (L4) | judge | eleven_tts `Daniel` | glb/wren.glb | Japanese-American, deliberate |
| av_niko | Niko "Fable" Kowalski | Adversarial critic (Critic role in Council) | score | eleven_tts `Freeman` | glb/niko.glb | Polish-American, sardonic |
| av_mira | Mira "The Hand" Singh | Human-in-the-loop cutaway host (end-of-clip comedy) | write_short | eleven_tts `Lily` | glb/mira.glb | Indian-American, droll |

>Each avatar's SKILL md lives at `icm/instructions/AVATAR_<avatar_id>.md`. Only one avatar acts per scene; concurrency causes them to "smoke a cigarette outside" (idle state).

## Voice command routing (R-04 WORLD.HUMAN_VOICE_COMMAND)
Intent classifications:
- `who owns this place` → av_paulie (front desk)
- `what's hot tonight` → av_marco (trend report)
- `how's the money` → av_zia (ledger)
- `post that` → av_dex (publisher, with SAFETY_JUDGE gate)
- `who's paying` / `confirmation` → av_wren (payment settled celebration)
- `tell me about <product>` → av_sasha
- `cut it` → av_niko (critic roasts)
- `human moment` → av_mira (cutaway)