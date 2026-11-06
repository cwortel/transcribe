# Lokale Transcriptie

Een lokale Mac-app die audio en video omzet in een bewerkbare transcriptie met Whisper. Daarna kun je ondertitels opslaan of met Qwen een samenvatting maken. De verwerking gebeurt op je eigen Mac.

Projectcontext en besluiten om later verder te gaan staan in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). Dit is een samenvatting voor overdracht, geen volledige chat-export.

## Benodigd

- Een Apple Silicon-Mac (M1 of nieuwer).
- Een internetverbinding voor de eenmalige installatie en het downloaden van de modellen.
- Python 3.12.
- Homebrew, om Python en FFmpeg te installeren.
- Ollama voor de lokale Qwen-samenvatting.
- Enkele GB vrije schijfruimte voor de lokale modellen. Qwen 3 8B gebruikt ongeveer 5,2 GB.

## Eenmalig installeren

Voer de stappen in volgorde uit. Open hiervoor **Terminal** (via Programma's > Hulpprogramma's > Terminal).

### 1. Installeer Homebrew, Python en FFmpeg

Als Homebrew nog niet is geïnstalleerd, volg dan de installatie-instructies op [brew.sh](https://brew.sh). Open daarna Terminal en voer uit:

```bash
brew install python@3.12 ffmpeg
```

### 2. Maak de Python-omgeving en installeer Whisper

Ga in Terminal naar de projectmap:

```bash
cd ~/Projects/Transcribe
```

Maak een aparte Python-omgeving aan en installeer de benodigde Whisper-software:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Download nu het Whisper-model alvast terwijl je internet hebt. De app gebruikt dit model daarna lokaal en offline:

```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='mlx-community/whisper-large-v3-turbo')"
```

Het downloaden kan even duren. Laat het Terminal-venster open totdat het commando klaar is.

### 3. Installeer Ollama en het samenvattingsmodel

1. Download en installeer Ollama voor Mac via [ollama.com/download](https://ollama.com/download).
2. Open de Ollama-app en laat die actief.
3. Open een nieuw Terminal-venster en download het model:

```bash
ollama pull qwen3:8b
```

Dit model is ongeveer 5,2 GB; het downloaden kan enige tijd duren.

### 4. Schakel Ollama-cloud uit

Om Ollama alleen lokaal te gebruiken, voer je dit uit in Terminal. Dit bewaart eventuele andere instellingen in het bestand:

```bash
python3 - <<'PY'
import json
from pathlib import Path

settings = Path.home() / ".ollama" / "server.json"
settings.parent.mkdir(parents=True, exist_ok=True)
config = json.loads(settings.read_text()) if settings.exists() else {}
config["disable_ollama_cloud"] = True
settings.write_text(json.dumps(config, indent=2) + "\n")
print("Ollama-cloud is uitgeschakeld. Herstart daarna Ollama.")
PY
```

Sluit Ollama af en open het opnieuw om de instelling toe te passen.

## De app starten

1. Open in Finder de map `~/Projects/Transcribe`.
2. Dubbelklik op `Start Transcriptie.command`.
3. Als macOS vraagt of je het bestand wilt openen, kies **Open**.
4. Laat het Terminal-venster open zolang je de app gebruikt. De app opent in je browser op [http://127.0.0.1:8765](http://127.0.0.1:8765).

Je kunt de app ook vanuit Terminal starten:

```bash
cd ~/Projects/Transcribe
./Start\ Transcriptie.command
```

Stop de app door in het Terminal-venster op **Control+C** te drukken.

## Een opname transcriberen en samenvatten

1. Kies **Audio- of videobestand** en selecteer een opname.
2. Kies **Nederlands** of **Automatisch herkennen**.
3. Klik op **Start transcriptie**. Tijdens het verwerken zie je de herkende tekst en de voortgang.
4. Controleer en bewerk de transcriptie. Je wijzigingen worden gebruikt voor ondertiteling en samenvatting.
5. Bewaar de transcriptie als HTML of kies SRT/VTT voor ondertitels.
6. Kies desgewenst een samenvattingstype en klik op **Maak samenvatting**.
7. De samenvatting verschijnt opgemaakt in de browser. Klik op **Bewaar samenvatting als HTML** en kies waar je het bestand wilt bewaren.

De app kan gangbare audio- en videoformaten verwerken, waaronder M4A, MP3, WAV, MP4, MOV, MKV en WebM. Het originele bestand wordt tijdens de verwerking tijdelijk lokaal opgeslagen en daarna verwijderd. De app luistert alleen op deze Mac (`127.0.0.1:8765`).

## Problemen oplossen

- **Whisper niet gevonden:** controleer of stap 2 is uitgevoerd en of `~/Projects/Transcribe/.venv/bin/mlx_whisper` bestaat.
- **Model niet beschikbaar of offlinefout:** download het Whisper-model opnieuw met het commando in stap 2 terwijl je internetverbinding hebt.
- **Ollama niet beschikbaar:** open de Ollama-app en controleer in Terminal met `ollama list` of `qwen3:8b` is geïnstalleerd.
- **Ollama-cloud wordt gemeld:** controleer de instelling uit stap 4 en herstart Ollama.
- **De browserpagina opent niet:** controleer of het Terminal-venster met de app nog open is en ga naar [http://127.0.0.1:8765](http://127.0.0.1:8765).

## Ontwikkelen en testen

Voer vanuit de projectmap uit:

```bash
.venv/bin/python -m unittest -v
.venv/bin/python -m py_compile app.py test_app.py
```
