from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
MODEL = "mlx-community/whisper-large-v3-turbo"
OLLAMA_MODEL = "qwen3:8b"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
CHUNK_CHARACTERS = 8_000
ALLOWED_EXTENSIONS = {
    ".aac", ".aiff", ".avi", ".flac", ".m4a", ".m4v", ".mkv", ".mov",
    ".mp3", ".mp4", ".mpeg", ".mpg", ".ogg", ".opus", ".wav", ".webm",
    ".wma", ".wmv",
}
SUMMARY_STYLES = {"meeting", "session", "general"}
WHISPER_SEGMENT_PATTERN = re.compile(
    r"^\[(?P<start>(?:\d+:)?\d{2}:\d{2}\.\d{3}) --> "
    r"(?P<end>(?:\d+:)?\d{2}:\d{2}\.\d{3})\]\s*(?P<text>.*)$"
)

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def find_whisper() -> str | None:
    configured = os.environ.get("MLX_WHISPER_BIN")
    candidates = [Path(configured)] if configured else []
    candidates.append(ROOT / ".venv/bin/mlx_whisper")
    candidates.extend(
        Path.home().glob(
            ".copilot/session-state/*/transcription-venv/bin/mlx_whisper"
        )
    )
    located = shutil.which("mlx_whisper")
    if located:
        candidates.append(Path(located))
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def chunk_text(text: str, limit: int = CHUNK_CHARACTERS) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for paragraph in (part.strip() for part in text.splitlines()):
        if not paragraph:
            continue
        pieces = [paragraph]
        if len(paragraph) > limit:
            pieces = []
            words = paragraph.split()
            piece = ""
            for word in words:
                if piece and len(piece) + len(word) + 1 > limit:
                    pieces.append(piece)
                    piece = ""
                piece = f"{piece} {word}".strip()
            if piece:
                pieces.append(piece)
        for piece in pieces:
            if current and current_size + len(piece) + 1 > limit:
                chunks.append("\n".join(current))
                current = []
                current_size = 0
            current.append(piece)
            current_size += len(piece) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def _ollama_chat(messages: list[dict[str, str]], max_tokens: int) -> str:
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 8192,
                "num_predict": max_tokens,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            data = json.loads(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Ollama is niet bereikbaar. Open de Ollama-app en probeer opnieuw."
        ) from exc
    content = data.get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("Het lokale model gaf geen tekst terug.")
    return content


def _summary_instructions(style: str) -> str:
    common = (
        "Schrijf in helder, natuurlijk Nederlands. Gebruik uitsluitend informatie "
        "uit de aangeleverde tekst. Verzin geen feiten, besluiten, namen, data of "
        "afspraken. Als iets onduidelijk is of ontbreekt, laat het weg of benoem "
        "dat het niet duidelijk is. Vat samen en herhaal geen transcriptiezinnen."
    )
    styles = {
        "meeting": (
            "Maak een duidelijk, beknopt vergaderverslag. Benoem, voor zover "
            "aanwezig: onderwerp, belangrijkste bespreekpunten, besluiten en "
            "actiepunten. Vermeld verantwoordelijke en termijn alleen wanneer "
            "die expliciet uit de tekst blijken. Laat smalltalk weg."
        ),
        "session": (
            "Maak een beknopt en zorgvuldig sessieverslag. Beschrijf de hulpvraag, "
            "de door de cliënt vertelde ervaringen, besproken thema's en expliciete "
            "afspraken of vervolg. Schrijf interpretaties toe aan degene die ze "
            "uitspreekt; stel geen diagnose en voeg geen behandeladvies toe dat "
            "niet in het transcript staat. Neem geen onnodige intieme details op."
        ),
        "general": (
            "Maak een korte, overzichtelijke samenvatting met de hoofdpunten, "
            "conclusies en eventuele expliciete vervolgacties."
        ),
    }
    return f"{common}\n{styles[style]}"


def summarize_text(text: str, style: str, job_id: str) -> str:
    chunks = chunk_text(text)
    if not chunks:
        raise RuntimeError("Er staat geen tekst in de transcriptie om samen te vatten.")

    instructions = _summary_instructions(style)
    summaries: list[str] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, 1):
        _update_job(
            job_id,
            message=f"Transcript verwerken: deel {index} van {total}",
            progress=round(index / total * 75),
        )
        summaries.append(
            _ollama_chat(
                [
                    {"role": "system", "content": instructions},
                    {
                        "role": "user",
                        "content": (
                            f"Vat dit deel beknopt samen. Bewaar belangrijke namen, "
                            f"besluiten en acties wanneer die er zijn.\n\n{chunk}"
                        ),
                    },
                ],
                max_tokens=650,
            )
        )

    round_number = 1
    while len(summaries) > 1:
        groups = [
            summaries[index:index + 4]
            for index in range(0, len(summaries), 4)
        ]
        combined: list[str] = []
        for index, group in enumerate(groups, 1):
            _update_job(
                job_id,
                message=f"Samenvatting samenvoegen (stap {round_number}, groep {index} van {len(groups)})",
                progress=min(75 + round_number * 8, 94),
            )
            combined.append(
                _ollama_chat(
                    [
                        {
                            "role": "system",
                            "content": instructions
                            + " Combineer de aangeleverde deelsamenvattingen tot "
                            "een samenhangend geheel. Behoud alle wezenlijke "
                            "punten, besluiten en actiepunten; voeg niets toe.",
                        },
                        {
                            "role": "user",
                            "content": "\n\n".join(group),
                        },
                    ],
                    max_tokens=750,
                )
            )
        summaries = combined
        round_number += 1

    _update_job(job_id, message="Eindversie opstellen", progress=96)
    return _ollama_chat(
        [
            {
                "role": "system",
                "content": instructions
                + " Lever een zelfstandig leesbaar eindverslag met een passende "
                "titel en duidelijke kopjes. Houd het beknopt maar volledig.",
            },
            {
                "role": "user",
                "content": f"Maak hiervan het eindverslag:\n\n{summaries[0]}",
            },
        ],
        max_tokens=1400,
    )


def _update_job(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if job:
            job.update(updates)
            job["updated"] = time.time()


def _parse_whisper_segment(line: str) -> tuple[float, float, str] | None:
    match = WHISPER_SEGMENT_PATTERN.match(line.strip())
    if not match:
        return None

    def parse_timestamp(value: str) -> float:
        parts = value.split(":")
        hours = int(parts[-3]) if len(parts) == 3 else 0
        minutes = int(parts[-2])
        seconds = float(parts[-1])
        return hours * 3600 + minutes * 60 + seconds

    text = match.group("text").strip()
    if not text:
        return None
    return parse_timestamp(match.group("start")), parse_timestamp(match.group("end")), text


def _probe_media_duration(
    media_path: Path, environment: dict[str, str]
) -> float | None:
    ffprobe = shutil.which("ffprobe", path=environment.get("PATH"))
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode:
        return None
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None
    return duration if duration > 0 else None


def _format_media_time(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"
    return f"{minutes:02d}:{whole_seconds:02d}"


def _transcribe(job_id: str, media_path: Path, language: str) -> None:
    job_dir = media_path.parent
    output_path = job_dir / "transcript.json"
    try:
        binary = find_whisper()
        if binary is None:
            raise RuntimeError(
                "Whisper is niet gevonden. Controleer of mlx-whisper is geïnstalleerd."
            )
        command = [
            binary,
            str(media_path),
            "--model", MODEL,
            "--output-format", "json",
            "--output-dir", str(job_dir),
            "--output-name", "transcript",
            "--condition-on-previous-text", "False",
            "--word-timestamps", "True",
            "--hallucination-silence-threshold", "2",
            "--verbose", "True",
        ]
        if language == "nl":
            command.extend(["--language", "Dutch"])
        environment = os.environ.copy()
        environment["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{environment.get('PATH', '')}"
        environment["HF_HUB_OFFLINE"] = "1"
        environment["PYTHONUNBUFFERED"] = "1"
        _update_job(
            job_id,
            message="Whisper laadt het lokale model en analyseert de opname",
            progress=None,
            transcript_preview="",
        )
        duration = _probe_media_duration(media_path, environment)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=environment,
        )
        output_tail: list[str] = []
        transcript_preview = ""
        try:
            if process.stdout is None:
                raise RuntimeError("Whisper-uitvoer kon niet worden gelezen.")
            for line in process.stdout:
                output_tail.append(line.rstrip())
                if len(output_tail) > 50:
                    output_tail.pop(0)
                segment = _parse_whisper_segment(line)
                if segment is None:
                    continue
                start, end, text = segment
                transcript_preview = (
                    f"{transcript_preview}\n[{_format_media_time(start)}] {text}"
                ).strip()
                if len(transcript_preview) > 5000:
                    transcript_preview = f"…\n{transcript_preview[-5000:]}"
                progress = (
                    min(99, max(0, round(end / duration * 100)))
                    if duration
                    else None
                )
                message = f"Spraak herkend tot {_format_media_time(end)}"
                if duration:
                    message += f" van {_format_media_time(duration)}"
                _update_job(
                    job_id,
                    message=message,
                    progress=progress,
                    transcript_preview=transcript_preview,
                )
            returncode = process.wait()
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if process.stdout is not None:
                process.stdout.close()
        if returncode:
            detail = "\n".join(output_tail)[-5000:].strip()
            raise RuntimeError(
                f"Whisper kon het bestand niet verwerken.\n{detail}"
            )
        if not output_path.is_file():
            raise RuntimeError("Whisper is klaar, maar er is geen transcriptbestand gevonden.")
        data = json.loads(output_path.read_text(encoding="utf-8"))
        segments = [
            {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": str(segment["text"]).strip(),
            }
            for segment in data.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        if not segments:
            raise RuntimeError(
                "Whisper heeft geen spraak herkend. Controleer of het bestand audio bevat."
            )
        _update_job(
            job_id,
            status="complete",
            message="Transcriptie klaar. Controleer de tekst en kies wat je wilt opslaan.",
            progress=100,
            segments=segments,
            language=data.get("language", language),
            filename=media_path.name,
        )
    except Exception as exc:
        _update_job(job_id, status="error", message=str(exc), progress=0)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def _summarize(job_id: str, text: str, style: str) -> None:
    try:
        result = summarize_text(text, style, job_id)
        _update_job(
            job_id,
            status="complete",
            message="Samenvatting klaar.",
            progress=100,
            summary=result,
        )
    except Exception as exc:
        _update_job(job_id, status="error", message=str(exc), progress=0)


def _prune_jobs() -> None:
    cutoff = time.time() - 8 * 60 * 60
    with JOBS_LOCK:
        old_ids = [
            job_id
            for job_id, job in JOBS.items()
            if job.get("updated", 0) < cutoff
        ]
        for job_id in old_ids:
            del JOBS[job_id]
        while len(JOBS) > 30:
            oldest_id = min(JOBS, key=lambda item: JOBS[item].get("updated", 0))
            del JOBS[oldest_id]


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalTranscriptie/1.0"

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _allowed_host(self) -> bool:
        return self.headers.get("Host", "") in {
            f"127.0.0.1:{PORT}",
            f"localhost:{PORT}",
        }

    def _allowed_origin(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin in {
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        }

    def _json(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self, max_bytes: int) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > max_bytes:
            raise ValueError("Ongeldige of te grote aanvraag.")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Ongeldige aanvraag.")
        return data

    def do_GET(self) -> None:
        if not self._allowed_host():
            self._json(403, {"error": "Alleen lokale verbindingen zijn toegestaan."})
            return
        path = urlparse(self.path).path
        if path == "/":
            body = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            self._json(200, self._status())
            return
        if path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/")
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                response = dict(job) if job else None
            if response is None:
                self._json(404, {"error": "Deze taak bestaat niet meer."})
            else:
                response.pop("updated", None)
                self._json(200, response)
            return
        self._json(404, {"error": "Niet gevonden."})

    def _status(self) -> dict[str, Any]:
        whisper = find_whisper()
        ollama_ok = False
        model_available = False
        local_only = False
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:11434/api/tags", timeout=2
            ) as response:
                models = json.loads(response.read()).get("models", [])
            ollama_ok = True
            model_available = any(
                model.get("name") == OLLAMA_MODEL for model in models
            )
            config_path = Path.home() / ".ollama/server.json"
            config = json.loads(config_path.read_text()) if config_path.exists() else {}
            local_only = (
                config.get("disable_ollama_cloud") is True
                or os.environ.get("OLLAMA_NO_CLOUD") == "1"
            )
        except (OSError, ValueError, urllib.error.URLError):
            pass
        return {
            "whisper_available": whisper is not None,
            "ollama_available": ollama_ok,
            "summary_model_available": model_available,
            "local_only": local_only,
        }

    def do_POST(self) -> None:
        if not self._allowed_host() or not self._allowed_origin():
            self._json(403, {"error": "Alleen lokale verbindingen zijn toegestaan."})
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/transcribe":
            self._start_transcription(parsed.query)
        elif parsed.path == "/api/summarize":
            self._start_summary()
        else:
            self._json(404, {"error": "Niet gevonden."})

    def _start_transcription(self, query: str) -> None:
        if find_whisper() is None:
            self._json(503, {"error": "mlx-whisper is niet gevonden op deze Mac."})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD_BYTES:
            self._json(413, {"error": "Bestand is leeg of groter dan 8 GB."})
            return
        params = urllib.parse.parse_qs(query)
        filename = Path(params.get("filename", ["audio"])[0]).name
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            self._json(400, {"error": "Dit audio- of videoformaat wordt niet ondersteund."})
            return
        language = params.get("language", ["nl"])[0]
        if language not in {"nl", "auto"}:
            self._json(400, {"error": "Onbekende taalkeuze."})
            return

        _prune_jobs()
        job_id = secrets.token_urlsafe(16)
        job_dir = Path(tempfile.mkdtemp(prefix="local-transcriptie-"))
        media_path = job_dir / f"media{extension}"
        try:
            with media_path.open("wb") as target:
                remaining = length
                while remaining:
                    block = self.rfile.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ValueError("Upload is onverwacht afgebroken.")
                    target.write(block)
                    remaining -= len(block)
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            self._json(400, {"error": str(exc)})
            return

        with JOBS_LOCK:
            JOBS[job_id] = {
                "kind": "transcription",
                "status": "running",
                "message": "Bestand ontvangen; Whisper start zo.",
                "progress": None,
                "filename": filename,
                "updated": time.time(),
            }
        threading.Thread(
            target=_transcribe,
            args=(job_id, media_path, language),
            daemon=True,
        ).start()
        self._json(202, {"job_id": job_id})

    def _start_summary(self) -> None:
        try:
            data = self._read_json(MAX_JSON_BYTES)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": f"Ongeldige aanvraag: {exc}"})
            return
        text = data.get("text")
        style = data.get("style")
        if not isinstance(text, str) or not text.strip():
            self._json(400, {"error": "De transcriptie bevat geen tekst."})
            return
        if len(text) > 10_000_000:
            self._json(413, {"error": "De transcriptie is groter dan 10 MB."})
            return
        if style not in SUMMARY_STYLES:
            self._json(400, {"error": "Kies een geldig samenvattingstype."})
            return
        status = self._status()
        if not status["ollama_available"] or not status["summary_model_available"]:
            self._json(
                503,
                {
                    "error": (
                        f"Het lokale model {OLLAMA_MODEL} is niet beschikbaar. "
                        "Open Ollama en controleer of het model is geïnstalleerd."
                    )
                },
            )
            return
        _prune_jobs()
        job_id = secrets.token_urlsafe(16)
        with JOBS_LOCK:
            JOBS[job_id] = {
                "kind": "summary",
                "status": "running",
                "message": "Transcript in delen verwerken met het lokale model.",
                "progress": 1,
                "updated": time.time(),
            }
        threading.Thread(
            target=_summarize,
            args=(job_id, text, style),
            daemon=True,
        ).start()
        self._json(202, {"job_id": job_id})


def main() -> None:
    if find_whisper() is None:
        print(
            "mlx-whisper is niet gevonden. Controleer de installatie voordat "
            "je de app gebruikt."
        )
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        raise SystemExit(
            f"De lokale app kan niet starten op poort {PORT}. "
            "Sluit eventueel een eerder geopend exemplaar."
        ) from exc
    url = f"http://{HOST}:{PORT}/"
    print(f"Lokale Transcriptie is beschikbaar op {url}")
    print("Laat dit venster open zolang je de app gebruikt. Druk Ctrl+C om te stoppen.")
    if not os.environ.get("LOCAL_TRANSCRIPTIE_NO_BROWSER"):
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nLokale Transcriptie wordt afgesloten.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
