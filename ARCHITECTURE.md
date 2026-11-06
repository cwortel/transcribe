# Architecture

This document describes the technical design and implementation decisions for the Transcribe application.

## Overview

A local macOS browser application that allows users to:
1. Select an audio or video file
2. Transcribe it with Whisper
3. Review and edit the transcription
4. Export as subtitles (SRT/VTT) or create a summary with local Qwen model

**Privacy**: All processing is local. Ollama cloud is disabled.

## Design Decisions

- **Server**: Python HTTP server listening on `http://127.0.0.1:8765`
- **Transcription**: `mlx-whisper==0.4.3` with `mlx-community/whisper-large-v3-turbo` model
- **Summarization**: Local Ollama model `qwen3:8b`
- **Default language**: Dutch; automatic language detection available
- **Output formats**: 
  - Transcript as HTML
  - Subtitles as SRT/VTT
  - Summary as formatted HTML (supports headings, bold, italic, lists)
- **Summary styles**: General, meeting notes (vergaderverslag), session notes (sessieverslag)
- **Editable transcription**: Users can review and edit before summarization or export

## Implementation Details

### File Structure

- `app.py`: HTTP server, Whisper processing, Qwen summarization logic
- `index.html`: Browser interface, progress display, transcription editor, exports
- `test_app.py`: Unit tests for helpers and prompt styles
- `requirements.txt`: Python dependencies
- `Start Transcriptie.command`: Finder launcher (double-click to start)
- `setup.command`: Automated setup (installs dependencies and models)
- `QUICKSTART.md`: Quick-start guide for users
- `README.md`: Full installation and usage documentation

### Processing Flow

1. User selects audio/video file
2. File is temporarily stored locally during processing
3. Whisper transcribes with settings: `--hallucination-silence-threshold 2` and `--condition-on-previous-text False`
4. Interface displays recognized sentences and progress based on audio timestamps
5. During model loading, an indeterminate progress indicator is shown
6. User can edit transcription before export or summarization
7. Qwen generates Markdown-formatted summaries
8. Browser converts Markdown formatting (headings, bold, italic, lists) to HTML
9. Temporary files are deleted after processing
10. User chooses where to save exports (browser's native save dialog)

### User Interface

- Transcription display includes a time column that adapts to full timestamp width
- Markdown summary formatting is preserved in HTML exports for copy-paste
- Server only listens on `127.0.0.1` (local machine only)

## Known Limitations & Considerations

### Whisper Accuracy
- Whisper may misrecognize Dutch words, proper nouns, or pronouns
- Transcription review by user is essential
- Hallucination suppression (`--hallucination-silence-threshold 2`) helps but doesn't eliminate issues
- Incorrect pronoun usage (e.g., "he" for female speakers) or unnatural phrasing has been observed
- User review cannot add information not in the audio

### Summarization
- Qwen summaries should be reviewed for accuracy and completeness
- Local models may misunderstand details or omit important context
- Summaries are not guaranteed to be error-free

### File Handling
- Files are saved to user-chosen locations via browser dialog (not automatically beside audio)
- Temporary processing files are cleaned up after transcription

### Testing
- Tests cover helpers and prompt styles in `test_app.py`
- Synthetic audio tested for upload, Whisper progress, live text display, and summarization
- Real-world testing recommended before production use

## Running the Application

### For Users
```bash
./Start\ Transcriptie.command
```
Automatically starts Ollama daemon and Python server. Terminates both on Ctrl+C.

### For Developers
```bash
ollama serve &  # Start Ollama daemon
.venv/bin/python app.py
```

### Setup
New installations should run:
```bash
./setup.command
```
This handles Python environment, dependency installation, and model downloads.

## Future Development

When continuing work on this project:
1. Read `README.md` for full installation and usage instructions
2. Review this file for architecture and design decisions
3. Check `test_app.py` for existing test coverage
4. Note that `.venv` and cached models already exist locally

Specific areas that may need attention:
- Whisper accuracy improvements (possibly through different settings or additional validation)
- Qwen summary quality and consistency
- Additional export formats or summary styles
- Performance optimization for large files
