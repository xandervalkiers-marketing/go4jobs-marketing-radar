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
    ('concurrent', 'Concurrentiecontent', 'AGO', 'site:ago.jobs interim rekrutering vacatures flexi-jobs', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Vivaldis', 'site:vivaldisinterim.be/nl interim vacature sollicitatie uitzend', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Adecco', 'site:adecco.be/nl-be interim arbeidsmarkt sollicitatie', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Start People', 'site:startpeople.be/nl/over-start-people/nieuws interim flexi jobs sollicitatie', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Accent', 'site:accentjobs.be/nl/blog jobs cv rekrutering', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Tempo-Team', 'site:tempo-team.be/nl/blog werk interim flexi', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Randstad', 'site:randstad.be werknemers werkgevers blog arbeidsmarkt', 'kandidaten en werkgevers'),
    ('concurrent', 'Concurrentiecontent', 'Unique', 'site:unique.be/nl/blog sollicitatie werk', 'kandidaten en werkgevers'),
]

KEYWORDS = ('werk', 'job', 'interim', 'uitzend', 'rekrut', 'sollicit', 'arbeids', 'vacatur',
            'kandidat', 'student', 'flexi', 'loon', 'werkgever', 'talent', 'logist', 'productie', 'hr')

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
        for title, link, date in results[:5]:
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
    previous=json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {}
    new=discover()
    # Preserve existing results when upstream is unavailable; don't publish blank content.
    if not new:
        print('Geen nieuwe RSS-resultaten. Bestaande data behouden.')
        return 0 if previous else 1
    # Historical, reviewed news stays in the baseline; fresh auto-discovery takes priority.
    base=previous.get('baseline',{})
    if not base:
        raise RuntimeError('baseline ontbreekt; verwijder de gecontroleerde startsignalen niet.')
    payload={'updated_at':TODAY.strftime('%Y-%m-%dT%H:%M:%SZ'),
             'update_mode':'automatische bronontdekking (niet inhoudelijk geverifieerd)',
             'sources_ok':len(set(i['source'] for i in new)),
             'baseline':base, 'live':new}
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Radar bijgewerkt:', len(new), 'nieuwe kandidaatartikels')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
