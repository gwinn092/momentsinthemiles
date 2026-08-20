# Narration files

Drop MP3s here and point at them from a post's front matter:

    audio: "/audio/the-miles-will-shape-you.mp3"
    audio_duration: "6:41"
    audio_reader: "Karlee"

The player renders only when `audio:` is set, so files can land one at a time.

## Recording notes
- **MP3, mono, 96–128 kbps.** Stereo doubles the file size and a voice recording
  gains nothing from it. A 7-minute essay should land around 5–6 MB.
- Read it the way you'd read it aloud to one person. The point of this is that it
  is *your* voice — a clean, slightly imperfect read beats a polished one.
- Say the title at the top. People arrive mid-scroll.
- `audio_duration` is shown to the reader so they know what they're committing to.
  Keep it accurate; it is the one number here worth being right.

## Why not auto-generated speech
Because the entire reason this exists is that it is Karlee or Jesse reading it.
A synthetic voice removes the only thing the feature is for.
