# Afweging platformkeuze: GovChat-NL updaten, kale Open WebUI, of LibreChat

*Status: concept ter besluitvorming, augustus 2026*

## Aanleiding

GovChat-NL is een fork van Open WebUI met aanpassingen voor de Nederlandse overheid. Bij het updaten van de fork naar Open WebUI v0.11.0 is de daadwerkelijke omvang van die aanpassingen in kaart gebracht. Die blijkt beperkt: **circa 2.000 regels eigen code**, waarvan een deel functionaliteit dekt die Open WebUI inmiddels ook standaard biedt. Dat roept de vraag op of het onderhouden van een eigen fork nog de juiste keuze is.

## Wat GovChat-NL feitelijk toevoegt aan Open WebUI

| Aanpassing | Omvang | Ook mogelijk met kale Open WebUI? |
|---|---|---|
| **Versimpelaar** (B1/B2-vereenvoudiging met chunking, meerdere generaties en selectie) | ~1.500 regels (backend-pipeline + UI) | Nee, dit is een echte eigen applicatie met een eigen LLM-pipeline |
| **App Launcher** (startscherm met app-tegels) | ~200 regels | Deels. Taakgerichte "apps" kunnen als workspace-model (systeemprompt + kennis + rechten), maar dan als optie in de model-dropdown, niet als tegel |
| **Per-app RBAC en per-app modelkeuze** | ~150 regels | Deels. Modeltoegang per groep is standaard; de app-laag erbovenop niet |
| **Nederlandstalige handleiding AI-geletterdheid** (conform AI-verordening) | ~700 regels content | Nee, maar het is content, geen techniek; herbruikbaar op elk platform |
| **Personalisatie-opties** (welkomstboodschap, UI-elementen verbergen, wachtwoordbeleid) | ~100 regels | Grotendeels. Open WebUI heeft steeds meer hiervan als instelling |
| **Nederlandse defaults en branding** | minimaal | Ja, via omgevingsvariabelen |

Conclusie uit de inventarisatie: het onderscheidende deel is de **Versimpelaar-pipeline** en de **handleiding**. De rest is dun of inmiddels door upstream ingehaald.

## Wat het onderhouden van de fork kost

Concreet gemeten bij de sync naar v0.11.0 (van 0.8.12, circa 5 maanden achterstand):

- **1.812 upstream-commits** verwerken, met **21 mergeconflicten**;
- upstream had de complete configuratie-architectuur vervangen en de modelselector verplaatst. De GovChat-aanpassingen moesten opnieuw worden ontworpen, niet alleen gemerged;
- na de merge waren meerdere regressies te verhelpen (crashende pagina's, een oneindige update-lus door een Svelte 5-gedragswijziging);
- doorlooptijd: ordegrootte een werkdag geconcentreerd werk, met kennis van beide codebases.

Dit is de terugkerende prijs: **elke maand niet syncen maakt de volgende sync duurder**. Daarnaast bleek uit een code-review van de fork-eigen code een reeks openstaande bugs (onder andere een XSS-kwetsbaarheid in de Versimpelaar-output en ontbrekende server-side permissiechecks) die alleen door de fork-beheerders opgelost kunnen worden.

## De drie opties

### Optie 1: doorgaan met een geüpdatete GovChat-NL (fork)

**Voor:**
- Er is al **draagvlak en een track record**: 700+ gebruikers bij meerdere overheden, een goedgekeurde DPIA als referentie, naamsbekendheid in het overheidsdomein;
- de Versimpelaar en de AI-geletterdheidshandleiding zijn direct beschikbaar en afgestemd op overheidstaken;
- volledige controle over defaults, taal en presentatie ("werkt out-of-the-box voor een ambtenaar");
- de fork is zojuist bijgewerkt naar v0.11.0, de achterstand is nu nul.

**Tegen:**
- structurele onderhoudslast bij elke upstream-sync (zie hierboven), afhankelijk van een of enkele beheerders;
- fork-eigen code kent eigen bugs en beveiligingsrisico's die niemand anders vindt of oplost;
- het functionele verschil met upstream wordt kleiner, waardoor de kosten/baten-verhouding elk jaar verslechtert.

### Optie 2: kale Open WebUI met configuratie

**Voor:**
- **Nul mergekosten**: updates zijn een versienummer ophogen;
- beveiligingsfixes en nieuwe functies (RAG, kennis, per-model rechten, personalisatie) komen vanzelf mee;
- vrijwel alles wat GovChat-NL doet is na te bouwen met standaardmiddelen: taak-apps als workspace-model met systeemprompt en kennis, toegangsbeheer per groep, Nederlandse taalinstelling, eigen branding via instellingen;
- grote community, veel documentatie.

**Tegen:**
- de **Versimpelaar** verdwijnt of moet herbouwd worden als losse dienst (bijvoorbeeld als aparte kleine webapp of als Open WebUI-tool/-function; dat kan, en isoleert de eigen code van de upstream-codebase);
- de handleiding moet elders worden aangeboden (kan als statische pagina of als "app" met documentatie);
- de App Launcher-presentatie vervalt: apps zijn dan modellen in een dropdown;
- draagvlak en DPIA zijn gekoppeld aan de naam GovChat-NL. Een overstap vergt hercommunicatie, al blijft de onderliggende techniek (en dus het grootste deel van de DPIA) gelijk.

### Optie 3: LibreChat

**Voor:**
- volwassen alternatief met sterke multi-provider-ondersteuning en agents;
- geen erfenis van de huidige fork.

**Tegen:**
- **alles begint opnieuw**: andere codebase (Node/React in plaats van Python/Svelte), geen van de GovChat-aanpassingen is herbruikbaar, DPIA-traject en draagvlak vanaf nul;
- geen inhoudelijk voordeel boven Open WebUI voor de huidige use-cases (chat, RAG, taak-apps);
- dezelfde forkvraag dient zich daar opnieuw aan zodra er overheidsspecifieke wensen zijn.

LibreChat is daarmee vooral een reëel alternatief als er fundamentele onvrede over Open WebUI zou zijn, en die is er niet.

## Afwegingskader

| Criterium | 1. GovChat-NL fork | 2. Kale Open WebUI | 3. LibreChat |
|---|---|---|---|
| Onderhoudslast | Hoog (syncs) | Laag | Laag, maar migratie zeer hoog |
| Functionaliteit vandaag | Volledig | Volledig minus Versimpelaar/handleiding/tegels | Vergelijkbaar, alles opnieuw inrichten |
| Draagvlak & DPIA | Aanwezig | Grotendeels herbruikbaar | Vanaf nul |
| Beveiligingsupdates | Vertraagd (via sync) | Direct | Direct |
| Eigen identiteit/branding | Sterk | Beperkt (instellingen) | Beperkt |
| Afhankelijkheid van eigen beheerders | Hoog | Laag | Laag |

## Licentie-aandachtspunt: rebranding is beperkt toegestaan

De Open WebUI-licentie (clausule 4, van kracht op alle code sinds begin 2025 en dus op de volledige huidige codebasis) verbiedt het aanpassen, verwijderen of vervangen van de "Open WebUI"-branding, behalve in drie gevallen:

1. deployments met maximaal **50 eindgebruikers** binnen een periode van 30 dagen;
2. **specifieke voorafgaande schriftelijke toestemming** van Open WebUI Inc.;
3. een **enterprise-licentie** die de aanpassing expliciet toestaat.

GovChat-NL vervangt de branding (eigen naam en presentatie) en wordt gebruikt door 700+ gebruikers. Zonder schriftelijke toestemming of enterprise-licentie is dat volgens de licentietekst een "material breach". Dit punt moet worden uitgezocht vóór elk besluit over doorontwikkeling: is die toestemming er, of moet die worden geregeld? Het geldt overigens voor elke optie waarin de naam GovChat-NL op de interface staat, ook voor een minimale fork die alleen branding bevat.

## Conclusie

De kern van de afweging:

1. **Technisch is GovChat-NL een kleine aanpassing.** Circa 2.000 regels eigen code op een codebase van honderdduizenden regels, waarvan een groot deel inmiddels ook met standaard Open WebUI-functionaliteit kan (taak-apps als workspace-model met systeemprompt, kennis en groepsrechten). Alleen de Versimpelaar-pipeline en de handleiding zijn echt eigen werk.
2. **De concepten zijn overdraagbaar.** App Launcher, Versimpelaar, taak-apps en de AI-geletterdheidshandleiding zijn ideeën en content, geen techniek die aan de fork vastzit. Ze kunnen worden meegenomen naar een kale Open WebUI-opzet (als tool, microservice, documentatie of configuratie), of naar welk platform dan ook.
3. **Het werkelijke voordeel van GovChat-NL is draagvlak, niet techniek.** De naam, de 700+ gebruikers, de goedgekeurde DPIA en de bekendheid binnen de overheid zijn waardevol. Maar dat draagvlak zit op het concept en de naam, niet op de circa 2.000 regels code eronder.
4. **Randvoorwaarde: de branding-kwestie.** De rebranding naar GovChat-NL vereist boven de 50 gebruikers toestemming of een enterprise-licentie van Open WebUI Inc. (zie hierboven). Dit moet eerst helder zijn; het bepaalt mede welke opties überhaupt beschikbaar zijn.

Kortom: kies op basis van draagvlak en licentiepositie, niet op basis van techniek, want technisch ontlopen de opties elkaar nauwelijks. De zojuist afgeronde update naar v0.11.0 maakt dat elke optie vanaf een schone, actuele situatie start.
