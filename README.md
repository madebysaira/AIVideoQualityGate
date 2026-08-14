# AIVideoQualityGate

A small, offline render check for AI video creators before a file goes to a client.

AI video usually fails in boring ways at the worst possible moment. The render has no audio. The aspect ratio is wrong. A generation contains a frozen or black section. The export has a strange frame rate, a missing stream, or audio that is far too quiet. These errors are easy to miss in a quick preview and awkward to discover after delivery.

`AIVideoQualityGate` runs `ffprobe` and optional `ffmpeg` checks against a render, then writes a short report with pass, warning, and failure results. It is designed for freelancers, small studios, and n8n or shell pipelines that need a cheap stop before client review.

## The two-minute payoff

```bash
python3 qualitygate.py render.mp4 --profile vertical --markdown report.md
```

You get:

- stream integrity and duration checks
- resolution, aspect ratio, frame rate, and codec checks
- audio-presence and audio-channel checks
- optional black-frame and frozen-frame detection
- optional loudness measurement when `ffmpeg` is available
- a Markdown report for a client-review folder
- JSON output for n8n, CI, or another automation step

Exit code `0` means the file passed. Exit code `1` means the gate found a failure. Exit code `2` means the local probe could not run, such as a missing `ffprobe` binary or unreadable file.

## Why a separate gate?

The generator should not be the delivery reviewer. Model APIs and editing tools can produce a valid-looking file with the wrong shape or an incomplete stream. Keeping the gate separate means it can run after Kling, Veo, Runway, ComfyUI, Remotion, ffmpeg, or a human export without changing the creative pipeline.

This is not a broadcast compliance system and it does not judge whether a shot is beautiful. It catches the mechanical mistakes that waste a review round.

## Profiles

| Profile | Intended output | Checks |
| --- | --- | --- |
| `vertical` | Reels, Shorts, TikTok | 1080×1920, portrait ratio, H.264 video, AAC audio |
| `horizontal` | YouTube, explainers, presentations | 1920×1080, landscape ratio, H.264 video, AAC audio |
| `square` | Feed and catalogue assets | 1080×1080, square ratio, H.264 video, AAC audio |
| `custom` | A project-specific contract | pass `--width`, `--height`, and optional codec/audio flags |

Profiles are deliberately conservative. A warning does not fail the gate unless `--strict` is used. A hard failure is reserved for a missing or unreadable stream and a clear contract violation.

## Install

There are no Python dependencies. You need:

- Python 3.9 or newer
- `ffprobe` on `PATH` for stream metadata checks
- `ffmpeg` on `PATH` for black, freeze, and loudness checks

On Debian or Ubuntu:

```bash
sudo apt install ffmpeg
```

The tool never uploads media and never calls an AI API.

## Examples

Basic report:

```bash
python3 qualitygate.py exports/hero.mp4
```

Vertical social delivery, with a Markdown report:

```bash
python3 qualitygate.py exports/hero.mp4 \
  --profile vertical \
  --markdown reports/hero.md \
  --json reports/hero.json
```

Machine-readable output for a batch job:

```bash
python3 qualitygate.py exports/*.mp4 \
  --profile vertical \
  --json reports/batch.json \
  --strict
```

The JSON contains one result per file, so a caller can route failures to a human review channel instead of blindly retrying generation.

## Decision tree

```text
Does the file open with ffprobe?
  no  → stop. Re-export or check the file path.
  yes ↓
Does it have exactly one usable video stream?
  no  → stop. Fix the export or stream selection.
  yes ↓
Does it match the delivery profile?
  no  → stop for delivery. Reframe, resize, or export again.
  yes ↓
Does it have the expected audio?
  no  → warn or fail, depending on the project contract.
  yes ↓
Are black/frozen sections or loudness problems reported?
  yes → review the timestamps before sending.
  no  → ready for human creative review.
```

## What the checks mean

- **Failure:** Do not send the file. The file is unreadable, has no video stream, or breaks a required profile contract.
- **Warning:** The file is technically usable but needs a human look. Examples include a missing optional audio stream or a detected black section.
- **Pass:** The mechanical check found no issue. This is not a creative approval.

A black frame can be intentional. A quiet audio track can be correct for a silent visual. The report gives timestamps and evidence so a person can decide instead of hiding a useful signal behind an automatic retry.

## Use with n8n

Run the command after the render/download step and before Drive upload or client notification. Read the process exit code:

```text
0 → continue to review/upload
1 → move to a review queue and include report.md
2 → alert the operator because the checker itself could not run
```

The command is safe to run repeatedly. It reads the input and writes reports only where you ask it to write them.

## Repository layout

```text
qualitygate.py             CLI entry point
qualitygate/
  checks.py                 Pure checks and result types
  probe.py                  ffprobe/ffmpeg adapters
  profiles.py               Delivery profiles
  report.py                 Text, Markdown, and JSON output
profiles/                   Editable project contracts
examples/                   Sample reports and batch usage
 tests/                     Dependency-free unit tests
```

## Limitations

- It cannot decide whether a generated face, product, logo, or motion path is correct.
- Black and freeze detection depends on `ffmpeg` filters and should be reviewed for intentional fades or holds.
- Loudness is reported when the local ffmpeg build exposes the `ebur128` filter. The tool does not normalize audio.
- The default profiles are examples. Change them for the actual delivery contract instead of treating social-media presets as universal rules.

## Research notes

The design was informed by:

- [FFmpeg filters documentation](https://ffmpeg.org/ffmpeg-filters.html), including `blackdetect`, `freezedetect`, and `ebur128`
- [FFprobe documentation](https://ffmpeg.org/ffprobe.html)
- [n8n faceless shorts workflow](https://n8n.io/workflows/17566-render-faceless-vertical-shorts-with-gemini-or-claude-edge-tts-and-ffmpeg/), which calls out ffmpeg/ffprobe as pipeline prerequisites
- [rendiffdev/rendiff-probe](https://github.com/rendiffdev/rendiff-probe), a broader FFmpeg/FFprobe QC project
- [slhck/ffmpeg-normalize](https://github.com/slhck/ffmpeg-normalize), a useful reference for loudness workflows
- Community discussions on exported audio/video sync and delivery failures, including [this Resolve report](https://www.reddit.com/r/davinciresolve/comments/1p36sv4/davinci_resolve_audio_and_video_out_of_sync_after_exporting_fix/)

## Contributing

Keep the core dependency-free. Add a focused check with a fixture or captured probe JSON, document false positives, and update the relevant profile only when the delivery contract really changed.

## License

MIT
