# Go4Jobs Marketing Radar — GitHub Pages editie

## Online zetten
1. Maak op https://github.com/new een **public** repository `go4jobs-marketing-radar` met een README-bestand (zodat de `main`-branch bestaat).
2. Pak dit ZIP-bestand uit en upload de mapinhoud in de hoofdmap van de repository. Bewaar de paden `scripts/update_radar.py` en `.github/workflows/radar-update.yml`.
3. Ga naar **Settings > Pages > Build and deployment > Source: GitHub Actions**. Kies **niet** Deploy from a branch.
4. Ga naar **Actions**, open **Go4Jobs Radar - dagelijks bijwerken en publiceren**, kies **Run workflow** (branch `main`).
5. Controleer de groene run en open https://GEBRUIKERSNAAM.github.io/go4jobs-marketing-radar/ (met je eigen GitHub-gebruikersnaam of organisatienaam).

Het dashboard en de gegevens worden via dezelfde workflow gepubliceerd. De workflow draait dagelijks rond 06:20 UTC (07:20 of 08:20 Belgische tijd, naargelang zomer- of winteruur). GitHub kan geplande runs vertragen of bij langdurige inactiviteit uitschakelen. Controleer dus geregeld de Actions-status.

## Wat het doet
- Leest Google News RSS-zoekopdrachten voor VDAB, Federgon, FOD Werkgelegenheid, Statbel, AGO, Vivaldis, Adecco, Accent, Randstad, Start People, Unique en Tempo-Team.
- Filtert titels grof op relevantie en ontdubbelt resultaten; nieuwe berichten zijn **niet inhoudelijk geverifieerd**.
- Toont bestaande Go4Jobs-blogalerts uit de startgegevens. Nieuwe juridische waarschuwingen worden **niet zelfstandig geverifieerd of toegevoegd**.
- Biedt een blogbriefing om in ChatGPT te gebruiken; schrijft nog geen blog automatisch binnen het dashboard.

## Veiligheid
GitHub Pages is **publiek zichtbaar**. Plaats geen interne dashboarddata, kandidaat- of klantgegevens, advertentiebudgetten, SharePoint-documenten of geheimen in deze repository. De RSS-gegevens zijn publiek; voor interne cijfers is later afgeschermde hosting nodig.

## Troubleshooting
- 404? Controleer `Settings > Pages`, wacht op een geslaagde deploy en verifieer URL/repositorynaam.
- Geen update? `Actions > Go4Jobs Radar - dagelijks bijwerken en publiceren > Run workflow`, bekijk logs.
- Geen workflow? Controleer dat `.github/workflows/radar-update.yml` daadwerkelijk op GitHub staat (de `.github`-map kan op Windows verborgen lijken).
- GitHub Actions uitgeschakeld? Zet ze aan in `Settings > Actions > General`.
