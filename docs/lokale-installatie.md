# GovChat-NL lokaal draaien op Windows (ontwikkelomgeving)

Deze handleiding beschrijft stap voor stap hoe je GovChat-NL (gebaseerd op Open WebUI v0.11.0) op een Windows-machine opzet in ontwikkelmodus, met hot reload voor frontend en backend.

## Vereisten

| Wat | Versie | Opmerking |
|---|---|---|
| Python | **3.11 of 3.12** | 3.13/3.14 werkt **niet** (dependency-pins van upstream) |
| Node.js | **18.13 t/m 22** | Nieuwere versies vereisen een override (zie stap 2) |
| Git | recent | |

> **Te nieuwe Python geïnstalleerd?** Je hoeft niets te verwijderen: installeer Python 3.12 (64-bit)
> ernaast via [python.org](https://www.python.org/downloads/), of gebruik `uv`
> (`pip install uv`, daarna `uv venv .venv --python 3.12` — uv downloadt zelf een beheerde 3.12).

## 1. Repository klonen

```powershell
git clone https://github.com/maartensukel/GovChat-NL.git
cd GovChat-NL
```

## 2. Frontend-dependencies installeren

```powershell
$env:npm_config_engine_strict = "false"   # alleen nodig op Node 23+
npm install
```

Dit zijn ~800 packages; reken op enkele minuten. Waarschuwingen als `npm warn deprecated` en de `npm audit`-melding aan het einde kun je negeren. Controleer daarna:

```powershell
Test-Path node_modules\pyodide            # moet True zeggen
```

## 3. Python-omgeving aanmaken

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt   # duurt enkele minuten, ~2 GB
pip install python-dotenv                 # nodig om .env te laten werken (ontbreekt in requirements)
```

> Weigert PowerShell de venv te activeren ("running scripts is disabled")? Voer eenmalig uit:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
>
> Krijg je `No matching distribution found for ...`? Dan gebruikt de venv een verkeerde Python-versie.
> Controleer met `python --version` — het moet 3.12.x zijn.

## 4. WEBUI_SECRET_KEY instellen (verplicht)

Sinds Open WebUI v0.11.0 is een expliciete secret key een harde vereiste. Maak in de **repo-root** (naast `package.json`) een `.env`-bestand met een random key:

```powershell
"WEBUI_SECRET_KEY='$(-join ((48..57)+(97..122) | Get-Random -Count 48 | % {[char]$_}))'" | Out-File -FilePath .env -Encoding ascii
Get-Content .env                          # ter controle
```

> **Belangrijk:** houd deze key stabiel. Alle inlogsessies zijn ermee ondertekend — verander je de key,
> dan is iedereen in één keer uitgelogd. Zet `.env` nooit in git.

## 5. Backend starten (terminal 1)

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
.\start_windows.bat
```

Wacht tot je `Uvicorn running on http://0.0.0.0:8080` ziet. De eerste start duurt langer (databasemigraties en het downloaden van het embedding-model).

> **Bekende quirk:** in ontwikkelmodus wist de backend bij het starten de bestanden in
> `backend/open_webui/static/` (logo, favicon). Dit is puur cosmetisch. Herstel ze met
> `git checkout -- backend/open_webui/static` en commit deze verwijderingen nooit per ongeluk mee.

## 6. Frontend starten (terminal 2)

```powershell
$env:npm_config_engine_strict = "false"   # alleen nodig op Node 23+
npm run dev
```

De eerste keer downloadt dit eenmalig de pyodide-bestanden (~100 MB). Open daarna **http://localhost:5173** — niet poort 8080; de frontend praat zelf met de backend.

## 7. Na de eerste start

De database begint leeg. Doorloop deze stappen:

1. **Registreer een account** — het eerste account wordt automatisch admin.
2. **Koppel een taalmodel-provider**: Admin-paneel → Instellingen → Connections
   (OpenAI-key, Azure via LiteLLM, of een lokale Ollama).
3. **Zet per model de "App Toegang"-vinkjes**: Admin → Instellingen → Modellen → model bewerken →
   sectie *App Toegang* → vink *Chat* (en eventueel *Versimpelaar*) aan.
   Zonder deze vinkjes toont de modelselector **"Geen modellen beschikbaar"** — dit is het
   bewuste allowlist-gedrag van GovChat-NL.
4. **(Optioneel) documenten-app inrichten**: Werkruimte → Kennis → collectie aanmaken →
   PDF's uploaden → de collectie koppelen aan een workspace-model met een systeemprompt.
   Voor gescande PDF's: zet OCR aan via Admin → Instellingen → Documenten →
   *PDF-afbeeldingen extraheren (OCR)*.

## Veelvoorkomende problemen

| Melding | Oorzaak | Oplossing |
|---|---|---|
| `Unsupported engine` bij `npm install` | Node 23+ | Override zetten (stap 2) of Node 22 installeren |
| `No matching distribution found for unstructured==...` | Python 3.13/3.14 | Venv opnieuw aanmaken met Python 3.12 (stap 3) |
| `Cannot find package 'pyodide'` bij `npm run dev` | `npm install` niet (volledig) gelukt | Stap 2 opnieuw uitvoeren, in dezelfde terminal als de override |
| `WEBUI_SECRET_KEY is not set` | `.env` wordt niet geladen | `pip install python-dotenv` en `.env` in de repo-root zetten, óf de variabele direct zetten: `$env:WEBUI_SECRET_KEY = "..."` vóór het starten |
| `Geen modellen beschikbaar` in de selector | App Toegang-vinkjes niet gezet | Zie stap 7.3 |
| Iedereen krijgt 401 na een herstart | `WEBUI_SECRET_KEY` gewijzigd | Gebruik altijd dezelfde key (daarom: in `.env`) |
| Logo/favicon-bestanden staan als *deleted* in `git status` | Static-wipe bij dev-start | `git checkout -- backend/open_webui/static` |
