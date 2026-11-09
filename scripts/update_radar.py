#!/usr/bin/env python3
"""Public-source-only news discovery for Go4Jobs Marketing Radar.
No API keys, CRM data or personal data. New headlines are *candidates*, not verified claims.
"""
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'radar-data.json'
TODAY = dt.datetime.now(dt.timezone.utc)

QUERIES = [
    ('sector', 'Arbeidsmarkt', 'VDAB', 'site:vdab.be/nieuws-voor-de-pers werkzoekenden vacatures', 'kandidaten en werkgevers'),
    ('sector', 'Uitzendmarkt', 'Federgon', 'site:federgon.be/nl/nieuws uitzendarbeid arbeidsmarkt', 'werkgevers en kandidaten'),
    ('sector', 'Regelgeving', 'FOD Werkgelegenheid', 'site:werk.belgie.be studentenarbeid flexi jobs arbeidsrecht', 'kandidaten en werkgevers'),
    ('sector', 'Werk & economie', 'Statbel', 'site:statbel.fgov.be arbeidsmarkt werkgelegenheid België', 'werkgevers en kandidaten'),
    ('concurrent', 'Concurrentiecontent', 'AGO', 'site:ago.jobs (blog OR nieuws OR advies OR arbeidsmarkt OR flexi-jobs) -vacatures -vacature -jobs', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Vivaldis', 'site:vivaldisinterim.be/nl (blog OR nieuws OR advies OR sollicitatie OR arbeidsmarkt) -vacatures -vacature -jobs', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Adecco', 'site:adecco.be/nl-be (blog OR nieuws OR arbeidsmarkt OR sollicitatietips) -vacatures -vacature', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Start People', 'site:startpeople.be/nl/over-start-people/nieuws interim flexi sollicitatie', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Accent', 'site:accentjobs.be/nl/blog cv rekrutering sollicitatie', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Tempo-Team', 'site:tempo-team.be/nl/blog werk interim flexi', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Randstad', 'site:randstad.be (workforce360 OR blog OR nieuws) arbeidsmarkt', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Unique', 'site:unique.be/nl/blog sollicitatie werk', 'kandidaten en werkgevers'),
]

KEYWORDS = ('werk', 'job', 'interim', 'uitzend', 'rekrut', 'sollicit', 'arbeids', 'vacatur',
            'kandidat', 'student', 'flexi', 'loon', 'werkgever', 'talent', 'logist', 'productie', 'hr')

# Concurrentie-overzicht: redactionele content, géén individuele jobadvertenties.
# Een artikel over het AANTAL vacatures blijft wél relevant (vooral in sectornieuws).
JOB_URL_RE = re.compile(
    r"/(?:vacatures?|jobs?|joboffers?|job-openings?|jobdetail|job-details|"
    r"vacature-detail|vacaturedetails|werken-bij|apply|solliciteer)(?:/|\?|$)", re.I)
JOB_TITLE_RE = re.compile(
    r"(?:^|[\s|:–-])(?:vacature|vacatures|jobaanbieding|jobopening|"
    r"openstaande vacature)(?:[\s|:–-]|$)|"
    r"\b(?:solliciteer (?:nu|vandaag)|we zoeken een|wij zoeken een|"
    r"gezocht:|jobs in [a-z]+|vacature voor|job als|aan de slag als|"
    r"werken als [a-z].*\b(?:bij|in)\b)\b", re.I)
# Bij 'vacatures dalen met 14%' gaat het duidelijk om marktnieuws.
MARKET_CONTEXT_RE = re.compile(
    r"\b(?:aantal vacatures|vacaturemarkt|vacaturecijfers|vacaturegraad|"
    r"vacatures (?:stijgen|dalen|nemen|groeien)|knelpuntvacatures|"
    r"arbeidsmarkt|trend|onderzoek|rapport|barometer)\b", re.I)

def is_individual_job(category, title, url=''):
    # Vacatureadvertenties horen nergens thuis in de Marketing Radar.
    if JOB_URL_RE.search(urllib.parse.urlparse(url).path):
        return True
    clean = re.sub(r'\s*[-–|]\s*[^-–|]{2,35}$', '', title).strip()
    if MARKET_CONTEXT_RE.search(clean):
        return False
    if JOB_TITLE_RE.search(clean):
        return True
    # Vooral Vivaldis/AGO leveren vacaturetitels als 'Heftruckchauffeur regio Gent | Vivaldis'.
    if re.match(r"^(?:operator|heftruckchauffeur|reachtruckchauffeur|magazijnier|"
                r"productiemedewerker|orderpicker|chauffeur|technieker|elektricien|"
                r"boekhouder|administratief medewerker|lasser|monteur|verkoper|"
                r"poetshulp|student|flexi(?:jobber)?|bediende)\b", clean, re.I):
        if not re.search(r"\b(?:tips|gids|waarom|hoe|wat|onderzoek|opleiding|"
                         r"voorwaarden|toekomst|evolutie)\b", clean, re.I):
            return True
    return False

def fetch_news(query):
    rss_url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
        'q': query + ' when:30d', 'hl': 'nl-BE', 'gl': 'BE', 'ceid': 'BE:nl'})
    res = requests.get(rss_url, headers={'User-Agent': 'Go4JobsMarketingRadar/2.0 (news-summary)'}, timeout=22)
    res.raise_for_status()
    root = ET.fromstring(res.content)
    out=[]
    for e in root.findall('./channel/item')[:12]:
        title = (e.findtext('title') or '').strip()
        link = (e.findtext('link') or '').strip()
        pub = (e.findtext('pubDate') or '').strip()
        if not title or not link: continue
        try:
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        except Exception:
            continue
        if (TODAY-date).days > 45 or date > TODAY + dt.timedelta(days=1): continue
        title = html.unescape(re.sub(r'<[^>]*>', '', title))
        if not any(k in title.lower() for k in KEYWORDS): continue
        out.append((title, link, date))
    return out

def get_id(category, url, title):
    return 'live-' + category + '-' + hashlib.sha1((url + title).encode()).hexdigest()[:13]

def discover():
    items=[]
    seen=set()
    for category, kind, source, query, audience in QUERIES:
        try:
            results=fetch_news(query)
            print(source, len(results), 'gevonden')
        except Exception as exc:
            print('Bron tijdelijk niet beschikbaar:', source, str(exc)[:170], file=sys.stderr)
            continue
        for title, link, date in results:
            if is_individual_job(category, title, link):
                continue
            canonical=re.sub(r'\s*[-–|]\s*(?:VDAB|Federgon|AGO|Vivaldis|Adecco|Accent|Randstad|Start People|Tempo.Team|Unique)\s*$', '', title, flags=re.I).strip()
            key=(source, canonical.casefold())
            if key in seen: continue
            seen.add(key)
            date_local=date.astimezone(dt.timezone(dt.timedelta(hours=1)))
            items.append({
                'id':get_id(category,link,canonical), 'category':category, 'kind':kind,
                'date':date_local.strftime('%d/%m/%Y'), 'sort':int(date.strftime('%Y%m%d')),
                'source':source, 'title':canonical,
                'summary':'Nieuw artikel gevonden bij '+source+'. De inhoud is nog niet redactioneel gecontroleerd; open de bron voor details.',
                'impact':'Mogelijke Go4Jobs-contentkans. Beoordeel de originele bron, de relevantie en eventuele cijfers of regels vóór je een blog laat schrijven.',
                'url':link, 'topic':canonical, 'audience':audience, 'priority':'Te beoordelen',
                'verification':'Automatisch gevonden · inhoud nog nakijken'
            })
    items.sort(key=lambda d:d['sort'], reverse=True)
    return items[:32]


def main():
    previous = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {}
    base = previous.get('baseline', {})
    if not base:
        raise RuntimeError('baseline ontbreekt; verwijder de gecontroleerde startsignalen niet.')

    discovered = discover()
    now_iso = TODAY.strftime('%Y-%m-%dT%H:%M:%SZ')
    previous_live = previous.get('live', [])
    first_seen = previous.get('first_seen_ids', {})
    if not isinstance(first_seen, dict):
        first_seen = {}
    # Bewaar de originele eerste ontdekking, ook als een artikel tijdelijk uit de feed valt.
    for item in previous_live:
        if item.get('id') and item.get('first_seen'):
            first_seen.setdefault(item['id'], item['first_seen'])
    for item in discovered:
        first_seen.setdefault(item['id'], now_iso)
        item['first_seen'] = first_seen[item['id']]
    # Bewaar bij een lege RSS-dag de vorige artikels, maar update de controledatum.
    live = discovered if discovered else previous_live
    live = [i for i in live if not is_individual_job(i.get('category'), i.get('title', ''), i.get('url', ''))]
    # Maximaal 180 dagen historie, zodat de JSON niet onbeperkt groeit.
    cutoff = TODAY - dt.timedelta(days=180)
    first_seen = {k: v for k, v in first_seen.items()
                  if isinstance(v, str) and _valid_recent_date(v, cutoff)}
    for item in live:
        if item.get('id') in first_seen:
            item['first_seen'] = first_seen[item['id']]

    payload = {
        'updated_at': now_iso,
        'update_mode': 'automatische bronontdekking (niet inhoudelijk geverifieerd)',
        'sources_ok': len(set(i['source'] for i in discovered)) if discovered else 0,
        'baseline': base, 'live': live,
        'first_seen_ids': first_seen,
        'new_count': sum(1 for i in discovered if i['first_seen'] == now_iso),
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Broncontrole voltooid:', len(discovered), 'kandidaatartikels;', payload['new_count'], 'voor het eerst gezien.')
    if not discovered:
        print('Geen RSS-resultaten; vorige artikels behouden en controledatum vernieuwd.')
    return 0


def _valid_recent_date(value, cutoff):
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')) >= cutoff
    except (TypeError, ValueError):
        return False


if __name__ == '__main__':
    raise SystemExit(main())
