"""Fetch a web page into a run's corpus, verbatim.

The research agent decides what to fetch; this module does the fetching and writes the file, so the
page text in the corpus is never written by a model. Every file gets a manifest entry with a hash of
its body, which the research gate checks.

Standard library only. HTML pages only. robots.txt is respected.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "kaizen-pmm-research/0.2 (+https://github.com/kAizentic/kaizen-pmm)"
TIMEOUT_S = 20
MAX_BYTES = 3_000_000
MIN_TEXT_CHARS = 400
MANIFEST = "_manifest.json"

SOURCE_TYPES = ("news_web", "deep_research_report", "community_forum", "vendor_page")
AUTHOR_RELATIONS = ("independent", "vendor", "competitor", "sponsored", "first_party")

_SKIP = frozenset({"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "button", "template"})
_BLOCK = frozenset({"p", "li", "h1", "h2", "h3", "h4", "h5", "blockquote", "td", "th", "pre", "figcaption", "dd", "dt"})
_DATE_META = (
    "article:published_time",
    "og:published_time",
    "datepublished",
    "date",
    "pubdate",
    "publish-date",
    "dc.date",
    "dc.date.issued",
)


class FetchError(Exception):
    pass


class _Extractor(HTMLParser):
    """Keeps readable text from content elements; drops navigation, scripts and chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.block: list[str] | None = None
        self.blocks: list[str] = []
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.time_datetime: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
            return
        if tag == "time" and a.get("datetime") and self.time_datetime is None:
            self.time_datetime = a["datetime"]
        if tag == "title":
            self._in_title = True
        if tag in _SKIP:
            self.skip_depth += 1
        elif tag in _BLOCK and self.skip_depth == 0:
            self._flush()
            self.block = []
        elif tag == "br" and self.block is not None:
            self.block.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in _SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in _BLOCK:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self.skip_depth == 0 and self.block is not None:
            self.block.append(data)

    def _flush(self) -> None:
        if self.block:
            text = re.sub(r"\s+", " ", "".join(self.block)).strip()
            if len(text) >= 2:
                self.blocks.append(text)
        self.block = None

    def close(self) -> None:
        self._flush()
        super().close()


@dataclass
class Page:
    url: str
    title: str
    text: str
    published: str | None
    author: str | None


def _robots_allows(url: str) -> bool:
    """RFC 9309: fetch robots.txt as ourselves; 2xx -> obey it, 4xx -> no rules, 5xx/unreachable -> disallow.

    robotparser.read() is not used: it requests robots.txt with Python's default user agent, which
    many sites answer with 403, and it then treats 403 as "disallow everything". Measured on
    Wikipedia, cfo.com and iofm.com: 403 to the default agent, 200 and allowed to ours.
    """
    parts = urllib.parse.urlsplit(url)
    req = urllib.request.Request(f"{parts.scheme}://{parts.netloc}/robots.txt", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read(500_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return 400 <= e.code < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(body.splitlines())
    return rp.can_fetch(USER_AGENT, url)


def _date(meta: dict[str, str], time_dt: str | None) -> str | None:
    for key in _DATE_META:
        v = meta.get(key)
        if v:
            m = re.match(r"\d{4}-\d{2}-\d{2}", v)
            if m:
                return m.group(0)
    if time_dt:
        m = re.match(r"\d{4}-\d{2}-\d{2}", time_dt)
        if m:
            return m.group(0)
    return None


def fetch_page(url: str) -> Page:
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise FetchError(f"not an http(s) URL: {url}")
    if not _robots_allows(url):
        raise FetchError(f"robots.txt disallows fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            ctype = resp.headers.get("Content-Type", "")
            if "html" not in ctype.lower():
                raise FetchError(f"not an HTML page ({ctype or 'no content type'}): {url}")
            raw = resp.read(MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
            final_url = resp.geturl()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"could not reach {url}: {e.reason}") from e
    if len(raw) > MAX_BYTES:
        raise FetchError(f"page larger than {MAX_BYTES} bytes: {url}")
    parser = _Extractor()
    parser.feed(raw.decode(charset, errors="replace"))
    parser.close()
    text = "\n\n".join(parser.blocks)
    if len(text) < MIN_TEXT_CHARS:
        raise FetchError(f"only {len(text)} characters of readable text at {url}; likely script-rendered or blocked")
    title = re.sub(r"\s+", " ", parser.meta.get("og:title") or parser.title).strip()
    return Page(
        url=final_url,
        title=title or final_url,
        text=text,
        published=_date(parser.meta, parser.time_datetime),
        author=parser.meta.get("author"),
    )


def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _slug(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    s = re.sub(r"[^a-z0-9]+", "-", f"{parts.netloc}{parts.path}".lower()).strip("-")
    return s[:80] or "page"


def load_manifest(corpus: Path) -> dict[str, dict]:
    p = corpus / MANIFEST
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_to_corpus(page: Page, corpus: Path, *, source_type: str, author_relation: str) -> Path:
    """Write the page as a corpus document and record it in the manifest. Returns the file path."""
    if source_type not in SOURCE_TYPES:
        raise FetchError(f"source_type must be one of {', '.join(SOURCE_TYPES)}")
    if author_relation not in AUTHOR_RELATIONS:
        raise FetchError(f"author_relation must be one of {', '.join(AUTHOR_RELATIONS)}")
    corpus.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(corpus)
    for name, entry in manifest.items():
        if entry["url"] == page.url:
            raise FetchError(f"already in the corpus as {name}")

    n = len(manifest) + 1
    name = f"{n:02d}-{_slug(page.url)}.md"
    fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
    domain = urllib.parse.urlsplit(page.url).netloc.lower()
    front = [
        "---",
        f"title: {json.dumps(page.title)}",
        f"url: {page.url}",
        f"domain: {domain}",
        f"source_type: {source_type}",
        f"source_platform: {domain}",
        f"author_relation: {author_relation}",
        f"author_type: {'individual' if page.author else 'organization'}",
        f"fetched_at: {fetched}",
    ]
    if page.published:
        front.append(f"published: {page.published}")
    front.append("---")
    body = page.text + "\n"
    (corpus / name).write_text("\n".join(front) + "\n" + body, encoding="utf-8", newline="\n")

    manifest[name] = {
        "url": page.url,
        "domain": domain,
        "fetched_at": fetched,
        "sha256": body_hash(body),
        "chars": len(body),
    }
    (corpus / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return corpus / name
