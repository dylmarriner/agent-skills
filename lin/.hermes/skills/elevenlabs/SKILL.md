---
name: elevenlabs
description: >
  ElevenLabs audio platform toolkit: (1) text-to-speech with premium voices, (2) multi-speaker dialogue,
  (3) automatic dubbing/translation, (4) voice synthesis and music generation, (5) sound effects.
  Use for: voiceovers, podcasts, audiobooks, video narration, content localization, IVR, e-learning.
  Uses inference.sh CLI for all ElevenLabs functionality.
license: MIT
metadata:
  author: inference-sh
  version: "1.0.0"
---

# ElevenLabs Audio Platform

Complete ElevenLabs toolkit via inference.sh CLI for all voice, dialogue, music, and dubbing needs.

## Quick Start

```bash
infsh login

# Generate speech
infsh app run elevenlabs/tts --input '{"text": "Hello world", "voice": "george"}'

# Generate dialogue (multi-speaker)
infsh app run elevenlabs/text-to-dialogue --input '{"segments": [{"text": "Hi", "voice": "george"}, {"text": "Hey", "voice": "aria"}]}'

# Dub to another language
infsh app run elevenlabs/dubbing --input '{"audio": "video.mp4", "target_lang": "es"}'
```

## Sub-Skills & Workflows

### 1. Text-to-Speech (TTS)

See: `references/tts-voiceover.md`
- 22+ premium female/male voices
- Models: Multilingual v2 (best quality), Turbo v2.5 (fast), Flash v2.5 (ultra-fast)
- Voice tuning: stability, similarity_boost, style
- 32 language support
- Formats: MP3 (44.1kHz), PCM

**Use cases:** Voiceovers, audiobooks, podcasts, IVR, accessibility e-learning narration

### 2. Multi-Speaker Dialogue

See: `references/dialogue-podcast.md`
- Create conversations with different voices in one audio file
- Voice direction tags: `[excitedly]`, `[sadly]`, `[whispering]`
- Podcast, interview, tutorial scenarios
- 2-4 speakers per dialogue

**Use cases:** Podcasts, audiobook character dialogue, training scenarios, explainer Q&A

### 3. Automatic Dubbing/Translation

See: `references/dubbing-localization.md`
- Translate & dub into 29 languages
- Auto speaker detection + voice preservation
- Maintain original timing and pacing
- Multi-speaker video support

**Use cases:** Content localization, multilingual e-learning, international marketing, podcast distribution

### 4. Music Generation

See: `references/music-background.md`
- AI music via ElevenLabs Music model
- Background tracks for dialogue/videos
- Adjustable duration and style
- Non-intrusive tracks for podcasts/narration

**Use cases:** Podcast intros/outros, background for YouTube videos, e-learning ambiance

### 5. Sound Effects

See: `references/sound-effects.md`
- AI-generated sound effects from text prompts
- Custom SFX for videos, games, presentations
- Short, reusable audio clips

**Use cases:** Video production, game audio, presentation SFX, app notifications

## Reference Files

### TTS
- `references/tts-voiceover.md` — Single-voice TTS master guide
- `references/voice-library.md` — All 22+ premium voices with styles
- `references/voice-tuning.md` — Stability, similarity_boost, style parameters
- `references/international-voices.md` — 32-language multilingual support

### Dialogue
- `references/dialogue-podcast.md` — Multi-speaker dialogue guide
- `references/voice-direction.md` — Direction tags for delivery control
- `references/podcast-workflow.md` — Full podcast production (dialogue + music)

### Dubbing
- `references/dubbing-localization.md` — Automatic dubbing master guide
- `references/language-support.md` — 29 supported target languages
- `references/localization-pipeline.md` — Dubbing + captioning workflow

### Music & SFX
- `references/music-background.md` — Background music generation
- `references/sound-effects.md` — AI sound effect generation

## Workflow Examples

### Podcast Production
1. Write episode script
2. Generate dialogue: `elevenlabs/text-to-dialogue`
3. Generate background music: `elevenlabs/music`
4. Merge: `infsh/media-merger`

### Video Localization Pipeline
1. Dub video: `elevenlabs/dubbing` (to target language)
2. Generate captions: `elevenlabs/stt` (transcribe dubbed audio)
3. Add captions: `infsh/caption-videos`
4. Delivered: localized video with SRT

### Audiobook Production
1. Generate narration: `elevenlabs/tts` (one voice for 90%)
2. Generate character dialogue: `elevenlabs/text-to-dialogue` (10% with multiple voices)
3. Generate SFX: `elevenlabs/sound-effects` (for dramatic moments)
4. Merge: `infsh/media-merger`

## Ground Rules

- **ALWAYS** use inference.sh CLI (`infsh`) for all ElevenLabs apps
- **ALWAYS** run `infsh login` first to authenticate
- **ALWAYS** test with short samples before generating full content
- **PREFER** ElevenLabs Multilingual v2 for highest quality
- **PREFER** Flash model for ultra-fast generation (<100ms)
- **PREFER** using dialogue over TTS for multi-character content
- **NEVER** generate long TTS (>10min continuous) in one call — chunk instead
- **NEVER** forget to merge background music after dialogue

## Related Skills

```bash
# ElevenLabs audio skills
npx skills add inference-sh/skills@elevenlabs-tts
npx skills add inference-sh/skills@elevenlabs-dialogue
npx skills add inference-sh/skills@elevenlabs-dubbing
npx skills add inference-sh/skills@elevenlabs-music
npx skills add inference-sh/skills@elevenlabs-sound-effects
npx skills add inference-sh/skills@elevenlabs-stt
npx skills add inference-sh/skills@elevenlabs-voice-changer
npx skills add inference-sh/skills@elevenlabs-voice-isolator

# Full platform (150+ apps)
npx skills add inference-sh/skills@infsh-cli
```

## Tools Required

- inference.sh CLI (`infsh`)
- Internet connection for API calls

## Troubleshooting

- **Voice missing?** Try different voice from library
- **Audio unclear?** Increase quality model (Multilingual v2), reduce style parameter
- **Dubbing poor quality?** Provide source language explicitly, ensure clean audio
- **Dialogue unnatural?** Add direction tags, reduce segment length

---

**Skill Type:** Audio Platform  
**Difficulty:** Intermediate  
**Estimated Time:** 1-5min per generation