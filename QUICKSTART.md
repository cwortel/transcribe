# Snel starten

## Voorbereiding (eenmalig)

Voer eerst `setup.command` uit om alle afhankelijkheden in te stellen:

```bash
./setup.command
```

Dit installeert Homebrew (als nodig), Ollama, Python-paketten en downloadt de modellen.

## De app starten

1. Open in Finder de map `~/Projects/Transcribe`.
2. Dubbelklik op `Start Transcriptie.command`.
3. Als macOS vraagt of je het bestand wilt openen, kies **Open**.
4. Laat het Terminal-venster open. De app opent in je browser op [http://127.0.0.1:8765](http://127.0.0.1:8765).

Of vanuit Terminal:

```bash
cd ~/Projects/Transcribe
./Start\ Transcriptie.command
```

Stop de app met **Control+C** in het Terminal-venster.

## Een opname transcriberen en samenvatten

1. Kies **Audio- of videobestand** en selecteer een opname.
2. Kies **Nederlands** of **Automatisch herkennen**.
3. Klik op **Start transcriptie**. Je ziet de herkende tekst en voortgang.
4. Controleer en bewerk de transcriptie.
5. Bewaar als HTML of kies SRT/VTT voor ondertitels.
6. Kies desgewenst een samenvattingstype en klik op **Maak samenvatting**.
7. Bewaar de samenvatting als HTML.

## Lokaal en privé

- Audio/video wordt met **Whisper** op jouw Mac verwerkt.
- Samenvattingen worden gemaakt door **Qwen 3 8B** via de lokale Ollama-daemon.
- De app luistert alleen op deze Mac (`127.0.0.1:8765`) — geen online verwerking.
- Alle modellen zijn al gedownload tijdens setup. De app werkt offline.
- Tijdelijke bestanden worden na verwerking automatisch verwijderd.

## Problemen oplossen

| Probleem | Oplossing |
|----------|-----------|
| "Kan niet starten op poort 8765" | Sluit een vorige sessie (Control+C in Terminal) |
| "Ollama niet bereikbaar" | Zorg dat `setup.command` volledig is afgerond |
| "Whisper niet gevonden" | Voer `setup.command` opnieuw uit |
| "App opent niet in browser" | Zorg dat het Terminal-venster nog open is; ga naar [http://127.0.0.1:8765](http://127.0.0.1:8765) |

Zie [README.md](README.md) voor uitgebreidere installatie- en probleemoplossingsdetails.
