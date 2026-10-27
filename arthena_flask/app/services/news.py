"""Veille éducative quotidienne : collecte, classement et déduplication."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from app.extensions import db
from app.models.news import EducationNews

NEWS_QUERIES = (
    ("fr", "\"Cameroun\" éducation établissement scolaire communiqué MINESEC MINEDUB"),
    ("fr", "\"Cameroun\" lycée collège école primaire examen enseignant"),
    ("en", "\"Cameroon\" education school teacher examination GCE"),
)
TRUSTED_DOMAINS = (
    "minedub.cm", "minesec.gov.cm", "unicef.org", "unesco.org",
    "cameroon-tribune.cm", "prc.cm", "spm.gov.cm",
)
KEYWORDS = {
    "decision": ("décision", "arrêté", "communiqué", "ministère", "minister", "decision"),
    "examen": ("examen", "concours", "gce", "baccalauréat", "probatoire", "exam"),
    "enseignant": ("enseignant", "teacher", "professeur", "recrutement", "formation"),
    "innovation": ("numérique", "digital", "innovation", "technologie", "ia "),
    "etablissement": ("école", "school", "lycée", "collège", "primaire", "campus"),
}
CAMEROON_MARKERS = (
    "cameroun", "cameroon", "yaoundé", "yaounde", "douala", "mineSec",
    "minedub", "obc", "gce board", "bafoussam", "garoua", "maroua", "bamenda",
)


def _clean(value):
    value = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _category(text):
    lowered = text.lower()
    scores = {name: sum(term in lowered for term in terms) for name, terms in KEYWORDS.items()}
    category, score = max(scores.items(), key=lambda item: item[1])
    return category if score else "education"


def _published(value):
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def _items_from_google_news(query, language):
    locale = "fr&gl=CM&ceid=CM:fr" if language == "fr" else "en&gl=CM&ceid=CM:en"
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl={locale}"
    request = Request(url, headers={"User-Agent": "ArthenaEducationWatch/1.0"})
    with urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    for item in root.findall("./channel/item")[:20]:
        title = _clean(item.findtext("title"))
        source_node = item.find("source")
        source = _clean(source_node.text if source_node is not None else "Source externe")
        link = _clean(item.findtext("link"))
        description = _clean(item.findtext("description"))
        source_url = (source_node.attrib.get("url", "") if source_node is not None else "")
        verified = any(domain in source_url.lower() for domain in TRUSTED_DOMAINS)
        country_text = f"{title} {description} {source} {source_url}".lower()
        if not any(marker.lower() in country_text for marker in CAMEROON_MARKERS):
            continue
        keyword_hits = sum(term in f"{title} {description}".lower() for terms in KEYWORDS.values() for term in terms)
        if keyword_hits < 1:
            continue
        yield {
            "title": title[:300],
            "summary": description[:650],
            "url": link[:1000],
            "source": source[:120],
            "category": _category(f"{title} {description}"),
            "language": language,
            "published_at": _published(item.findtext("pubDate")),
            "relevance_score": keyword_hits + (5 if verified else 0),
            "is_verified_source": verified,
        }


def refresh_education_news():
    """Actualise la veille et renvoie (ajouts, erreurs), sans texte généré."""
    added, errors = 0, []
    # Nettoie les anciennes collectes qui ne mentionnent pas clairement le Cameroun.
    for article in EducationNews.query.all():
        country_text = f"{article.title} {article.summary} {article.source}".lower()
        education_hits = sum(
            term in country_text for terms in KEYWORDS.values() for term in terms
        )
        if not any(marker.lower() in country_text for marker in CAMEROON_MARKERS) or education_hits < 1:
            db.session.delete(article)
    db.session.commit()
    seen_urls = {url for (url,) in db.session.query(EducationNews.url).all()}
    for language, query in NEWS_QUERIES:
        try:
            for data in _items_from_google_news(query, language):
                if not data["title"] or not data["url"]:
                    continue
                if data["url"] in seen_urls:
                    existing = EducationNews.query.filter_by(url=data["url"]).first()
                    if existing:
                        existing.relevance_score = max(existing.relevance_score, data["relevance_score"])
                        existing.is_verified_source = existing.is_verified_source or data["is_verified_source"]
                    continue
                db.session.add(EducationNews(**data))
                seen_urls.add(data["url"])
                added += 1
            db.session.commit()
        except Exception as exc:  # la panne d'une source ne bloque jamais l'application
            db.session.rollback()
            errors.append(f"{language}: {type(exc).__name__}")
    return added, errors


def latest_news(limit=12):
    return (
        EducationNews.query
        .order_by(EducationNews.is_verified_source.desc(), EducationNews.published_at.desc())
        .limit(limit)
        .all()
    )
