# Review en advies huidige GovChat-NL-deployment

*Status: concept, augustus 2026*

## Samenvatting

De huidige deployment staat qua opzet goed: een aparte database en een servicecontainer vormen een degelijke basis. Er zijn vier verbeterpunten met prioriteit: de secret key expliciet instellen (oorzaak van de 401-fouten), secretsbeheer via een vault, de geplande update naar Open WebUI v0.11.0 uitrollen (lost bekende stabiliteitsproblemen op) en op termijn backend en frontend splitsen. Daarnaast liggen er drie concrete kansen: een Databricks-gateway met geanonimiseerde gebruikersinformatie, koppeling met Microsoft Entra ID, en het met beperkte aanpassingen aanbieden van agents die documenten bevraagbaar maken en via Python-tools ook externe bronnen kunnen benaderen.

## Huidige situatie: wat goed staat

- **Scheiding van data en applicatie.** Er draait een aparte database naast de servicecontainer. Daarmee zijn upgrades en herstarts van de applicatie mogelijk zonder dataverlies, en is een backup-strategie op de database te richten.
- **Containerized opzet.** De applicatie draait als container, wat reproduceerbare deployments en eenvoudige rollbacks mogelijk maakt.
- **Backend en frontend in één container is voor de huidige schaal prima.** Open WebUI is hier ook op ingericht: de backend serveert de gebouwde frontend. Aandachtspunt voor later staat hieronder.

## Bevindingen en aanbevelingen

### 1. 401-fouten: secret key is niet ingesteld (prioriteit: hoog)

De waargenomen 401-fouten worden veroorzaakt doordat `WEBUI_SECRET_KEY` niet expliciet is ingesteld. De applicatie genereert dan zelf een sleutel per container(start). Alle inlogsessies zijn JWT's die met deze sleutel zijn ondertekend; bij een nieuwe container of een tweede replica ontstaat een andere sleutel en zijn bestaande sessies ongeldig. Dat uit zich als willekeurige of massale 401's.

**Advies:** stel `WEBUI_SECRET_KEY` expliciet in als omgevingsvariabele, identiek op alle instanties, en houd de waarde stabiel over deployments heen. Let op: vanaf Open WebUI v0.11.0 is dit een harde vereiste; de applicatie start dan niet meer zonder. Eenmalig gevolg van het (opnieuw) zetten van de sleutel is dat alle gebruikers opnieuw moeten inloggen.

### 2. Secretsbeheer: vault opzetten (prioriteit: hoog)

Secrets (de secret key, API-sleutels van modelproviders, databasewachtwoorden) horen niet in plaintext in containerconfiguratie of repository. **Advies:** zet een vault op (bijvoorbeeld Azure Key Vault of HashiCorp Vault) en injecteer secrets bij het starten van de container. Dit sluit aan op de eis uit punt 1: de secret key krijgt zo een vaste, veilig beheerde plek in plaats van een gegenereerd bestand in de container.

### 3. Update naar Open WebUI v0.11.0 uitrollen (prioriteit: hoog)

De fork is bijgewerkt naar Open WebUI v0.11.0 (vanaf 0.8.12, ruim 1.800 upstream-commits). Deze update bevat een groot aantal stabiliteits- en beveiligingsfixes en zou de bekende stabiliteitsproblemen in de huidige deployment moeten verhelpen. Aandachtspunten bij de uitrol:

- `WEBUI_SECRET_KEY` moet vooraf gezet zijn (zie punt 1);
- alle gebruikers moeten na de upgrade eenmalig opnieuw inloggen;
- de databasemigraties draaien automatisch bij de eerste start; plan een kort onderhoudsvenster en een databasebackup vooraf.

### 4. Backend en frontend op één container (prioriteit: laag, monitoren)

Voor de huidige schaal is één container prima. Bij groei ontstaan er wel beperkingen: schalen kan alleen als geheel, een frontend-wijziging vereist een volledige rebuild, en de backend (LLM-verkeer, RAG-indexering) en frontend (statische bestanden) hebben heel verschillende resourceprofielen. **Advies:** nu niets doen, maar bij schaalgroei de frontend als statische bestanden achter een CDN of aparte webserver zetten en de backend zelfstandig horizontaal schalen. Voorwaarden daarvoor zijn een gedeelde database (staat er al), een gedeelde Redis voor sessie- en socketstate, en een identieke secret key op alle replicas (punt 1).

## Kansen voor doorontwikkeling

### A. Databricks-gateway met geanonimiseerde gebruikersinformatie

Het is mogelijk het LLM-verkeer via een Databricks-gateway te routeren. Voordelen: centraal kosten- en gebruiksinzicht, rate limiting per team, en één plek voor modelbeheer. Door gebruikersinformatie te anonimiseren of pseudonimiseren voordat die de gateway bereikt (Open WebUI kan gebruikersinfo als headers meesturen; dit staat standaard uit en kan bewust uit blijven of gepseudonimiseerd worden ingevuld) blijft de analyse mogelijk zonder herleidbaarheid tot personen. Dit past goed bij de bestaande DPIA-lijn.

### B. Microsoft Entra ID koppelen

Open WebUI ondersteunt OAuth/OIDC out-of-the-box, inclusief Microsoft Entra ID. Daarmee vervalt lokaal wachtwoordbeheer, sluit toegang aan op het bestaande joiner/mover/leaver-proces en kunnen Entra-groepen doorvertaald worden naar rollen en groepsrechten in de applicatie. **Advies:** inrichten via de standaard OAuth-configuratie (client-id, tenant, group mapping) en gelijktijdig het lokale inlogformulier uitzetten voor reguliere gebruikers.

### C. Agents: documenten bevraagbaar maken en verder

Met beperkte aanpassingen (grotendeels configuratie, geen forkcode) zijn taakgerichte agents te maken:

- **Documenten bevraagbaar maken.** Een kenniscollectie (PDF-upload, OCR, automatische chunking en vector-opslag) gekoppeld aan een workspace-model met een systeemprompt levert een agent op die vragen over die documenten beantwoordt met bronvermelding. Dit is met de huidige versie al gedemonstreerd (CAO-vragenbeantwoorder) en vereist geen codewijziging.
- **Complexere agents via Python-tools.** Open WebUI ondersteunt tools en functions: Python-scripts die het model tijdens een gesprek kan aanroepen. Daarmee kunnen agents ook websites benaderen, API's bevragen, berekeningen uitvoeren of gegevens uit interne systemen ophalen. Aandachtspunt: tools draaien servercode; beperk wie tools mag installeren tot beheerders en beoordeel scripts vooraf (supply-chain- en datalekrisico).
- Desgewenst zijn zulke agents als tegel in de App Launcher te presenteren, zodat ze voor eindgebruikers als aparte apps voelen.

## Prioritering

| # | Actie | Prioriteit | Inspanning |
|---|---|---|---|
| 1 | `WEBUI_SECRET_KEY` expliciet en stabiel instellen | Hoog | Klein |
| 2 | Vault opzetten en secrets migreren | Hoog | Middel |
| 3 | Update naar v0.11.0 uitrollen (met backup en onderhoudsvenster) | Hoog | Middel |
| 4 | Entra ID-koppeling inrichten | Middel | Middel |
| 5 | Databricks-gateway met anonimisering | Middel | Middel |
| 6 | Documenten-agents inrichten (kennis + workspace-modellen) | Middel | Klein |
| 7 | Python-tools voor complexere agents, met beheerproces | Laag | Middel |
| 8 | Backend/frontend splitsen | Laag (bij schaalgroei) | Groot |

Punten 1 t/m 3 horen bij elkaar en kunnen in één onderhoudsmoment: secret key uit de vault, update uitrollen, iedereen logt eenmalig opnieuw in.
