# Lokale Transcriptie

Een lokale Mac-app die audio en video omzet in een bewerkbare transcriptie met Whisper. Daarna kun je ondertitels opslaan of met Qwen een samenvatting maken. De verwerking gebeurt op je eigen Mac.

Voor technische details en architectuurkeuzes, zie [ARCHITECTURE.md](ARCHITECTURE.md). Voor snelle start, zie [QUICKSTART.md](QUICKSTART.md).

## Vereisten

- Apple Silicon-Mac (M1 of nieuwer)
- Ongeveer 5-6 GB vrije schijfruimte (voor modellen)
- Internetverbinding (eenmalig, voor setup)

## Snel starten

1. **Setup** (eenmalig):
   ```bash
   ./setup.command
   ```
   Dit installeert alle afhankelijkheden automatisch (Homebrew, Ollama, Python-paketten, modellen).

2. **App starten**:
   ```bash
   ./Start\ Transcriptie.command
   ```
   De app opent in je browser op [http://127.0.0.1:8765](http://127.0.0.1:8765).

3. **App afsluiten**:
   Druk **Control+C** in het Terminal-venster.

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

### Setup problemen

| Probleem | Oplossing |
|----------|-----------|
| "Python 3 not found" | Download Python van [python.org](https://www.python.org/downloads/macos/) en installeer het |
| "Homebrew installation failed" | Controleer je internetverbinding; zie [brew.sh](https://brew.sh) voor systeemvereisten |
| "Failed to install dependencies" | Voer `setup.command` opnieuw uit; controleer vrije schijfruimte (minimaal 6 GB) |
| Model download is langzaam | De modellen zijn groot (~5 GB); dit kan 15-30 minuten duren afhankelijk van je internetsnelheid |

### App problemen

| Probleem | Oplossing |
|----------|-----------|
| "Kan niet starten op poort 8765" | Sluit een vorige sessie: zoek het Terminal-venster van de app en druk **Control+C** |
| "Ollama niet bereikbaar" | Zorg dat `setup.command` volledig is afgerond; herstart de app |
| "Whisper niet gevonden" | Voer `setup.command` opnieuw uit; controleer of `.venv/bin/mlx_whisper` bestaat |
| "App opent niet in browser" | Zorg dat het Terminal-venster nog open is; ga naar [http://127.0.0.1:8765](http://127.0.0.1:8765) |
| "Transcriptie is leeg of onvoltooid" | Controleer of het audio-/videobestand niet beschadigd is; probeer een ander formaat (MP3, WAV, MP4) |
| "Samenvatting werkt niet" | Controleer of Ollama correct is ingesteld: voer `ollama list` uit in Terminal en controleer of `qwen3:8b` aanwezig is |

### Transcriptie kwaliteit

- **Whisper herkent Nederlands slecht**: Whisper werkt het beste met Nederlands van moedertaalsprekers; zware accenten kunnen problemen veroorzaken
- **Foute woorden of voornaamwoorden**: Dit is normaal bij spraakherkenning; controleer en corrigeer altijd de transcriptie
- **Hallucinaties of herhaling**: Wijzigingen in stille-instellingen kunnen helpen; zie Advanced Setup

## Advanced Setup (handmatige installatie)

Als `setup.command` niet werkt of je wilt stappen handmatig uitvoeren:

### 1. Installeer Homebrew, Python en FFmpeg

Open Terminal en voer uit:

```bash
# Installeer Homebrew (als nog niet geïnstalleerd)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installeer Python 3.12 en FFmpeg
brew install python@3.12 ffmpeg
```

### 2. Zet Python-omgeving op

```bash
cd ~/Projects/Transcribe
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Download het Whisper-model:

```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='mlx-community/whisper-large-v3-turbo')"
```

### 3. Installeer en configureer Ollama

Download van [ollama.com/download](https://ollama.com/download).

Download het Qwen-model:

```bash
ollama pull qwen3:8b
```

Schakel Ollama-cloud uit voor privacy:

```bash
python3 - <<'PY'
import json
from pathlib import Path

settings = Path.home() / ".ollama" / "server.json"
settings.parent.mkdir(parents=True, exist_ok=True)
config = json.loads(settings.read_text()) if settings.exists() else {}
config["disable_ollama_cloud"] = True
settings.write_text(json.dumps(config, indent=2) + "\n")
print("Ollama-cloud is uitgeschakeld.")
PY
```

## Ontwikkelen en testen

Voer vanuit de projectmap uit:

```bash
.venv/bin/python -m unittest -v
.venv/bin/python -m py_compile app.py test_app.py
```
