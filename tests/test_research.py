"""Research stage: the fetcher writes the corpus, the gate proves nobody else did."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import kaizen.gate as gate
from kaizen.fetch import FetchError, fetch_page, save_to_corpus
from kaizen.gate import run_gate

PARA = "Finance teams report that invoice approvals wait on budget owners outside finance for days at a time. "


def _article(title: str, date: str | None, paragraphs: int = 6) -> str:
    meta = f'<meta property="article:published_time" content="{date}T09:00:00Z">' if date else ""
    body = "".join(f"<p>{PARA}Point {i}.</p>" for i in range(paragraphs))
    return (
        f"<html><head><title>{title}</title>{meta}<script>var tracking = 1;</script></head><body>"
        f"<nav><a href='/'>Home</a> Menu Pricing Login</nav><article><h1>{title}</h1>{body}</article>"
        f"<footer>Copyright footer text</footer></body></html>"
    )


PAGES = {
    "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /private\n"),
    "/a": ("text/html; charset=utf-8", _article("Approval delays in AP", "2026-05-04")),
    "/b": ("text/html", _article("Exceptions eat AP hours", "2026-06-10")),
    "/c": ("text/html", _article("Auditors and payment controls", None)),
    "/d": ("text/html", _article("Spreadsheet approvals persist", "2026-07-01")),
    "/e": ("text/html", _article("ERP modules and routing", "2026-07-15")),
    "/private": ("text/html", _article("Hidden", "2026-01-01")),
    "/report.pdf": ("application/pdf", "%PDF-1.4"),
    "/thin": ("text/html", "<html><body><p>Too short.</p></body></html>"),
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        # Like many real sites: refuse robots.txt to clients that do not identify themselves.
        if self.path == "/robots.txt" and "kaizen-pmm" not in self.headers.get("User-Agent", ""):
            self.send_response(403)
            self.end_headers()
            return
        ctype, body = PAGES.get(self.path, ("text/html", ""))
        if not body:
            self.send_response(404)
            self.end_headers()
            return
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args) -> None:
        pass


@pytest.fixture(scope="module")
def server():
    """Two servers, so the corpus spans two sites (a site is host plus port)."""
    servers = [ThreadingHTTPServer(("127.0.0.1", 0), _Handler) for _ in range(2)]
    for s in servers:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    yield [f"http://127.0.0.1:{s.server_address[1]}" for s in servers]
    for s in servers:
        s.shutdown()


@pytest.fixture
def run(tmp_path: Path) -> Path:
    d = tmp_path / "runs" / "r"
    d.mkdir(parents=True)
    return d


def _fetch(run: Path, url: str, st: str = "news_web", rel: str = "independent") -> Path:
    return save_to_corpus(fetch_page(url), run / "corpus", source_type=st, author_relation=rel)


def _plan(run: Path, question: str = "Where do mid-market AP teams lose the most time?") -> None:
    manifest = json.loads((run / "corpus" / "_manifest.json").read_text())
    plan = {
        "stage": "research",
        "questions": [question],
        "queries": ["mid-market accounts payable approval delays"],
        "sources": [{"file": f, "question": question} for f in manifest],
    }
    (run / "research.json").write_text(json.dumps(plan), encoding="utf-8")


def _codes(report) -> list[str]:
    return [v.code for v in report.violations]


@pytest.fixture
def researched(run: Path, server, monkeypatch) -> Path:
    monkeypatch.setattr(gate, "MIN_RESEARCH_DOMAINS", 2)
    host_a, host_b = server
    for i, p in enumerate(("/a", "/b", "/c", "/d", "/e")):
        _fetch(run, (host_a if i % 2 == 0 else host_b) + p, st="deep_research_report" if p == "/a" else "news_web")
    _plan(run)
    return run


# --- fetcher --------------------------------------------------------------------------------


def test_fetch_keeps_content_and_drops_chrome(run: Path, server) -> None:
    path = _fetch(run, server[0] + "/a")
    text = path.read_text(encoding="utf-8")
    assert "published: 2026-05-04" in text
    assert PARA.strip() in text
    assert "Menu Pricing Login" not in text and "tracking" not in text and "Copyright footer" not in text
    manifest = json.loads((run / "corpus" / "_manifest.json").read_text())
    assert manifest[path.name]["sha256"]


def test_fetch_respects_robots(run: Path, server) -> None:
    with pytest.raises(FetchError, match="robots"):
        fetch_page(server[0] + "/private")


def test_fetch_refuses_non_html(server) -> None:
    with pytest.raises(FetchError, match="not an HTML page"):
        fetch_page(server[0] + "/report.pdf")


def test_fetch_refuses_thin_pages(server) -> None:
    with pytest.raises(FetchError, match="readable text"):
        fetch_page(server[0] + "/thin")


def test_fetch_refuses_duplicates(run: Path, server) -> None:
    _fetch(run, server[0] + "/a")
    with pytest.raises(FetchError, match="already in the corpus"):
        _fetch(run, server[0] + "/a")


def test_undated_page_has_no_invented_date(run: Path, server) -> None:
    assert "published:" not in _fetch(run, server[0] + "/c").read_text(encoding="utf-8")


# --- research gate --------------------------------------------------------------------------


def test_research_gate_passes(researched: Path) -> None:
    rpt = run_gate("research", researched, researched.parent.parent)
    assert rpt.passed, rpt.violations
    assert "undated_source" in [w.code for w in rpt.warnings]


def test_edited_document_fails(researched: Path) -> None:
    doc = sorted((researched / "corpus").glob("*.md"))[0]
    doc.write_text(doc.read_text(encoding="utf-8").replace("budget owners", "nobody"), encoding="utf-8")
    assert "document_modified" in _codes(run_gate("research", researched, researched.parent.parent))


def test_agent_written_document_fails(researched: Path) -> None:
    (researched / "corpus" / "99-my-summary.md").write_text(
        "---\nsource_type: deep_research_report\nauthor_relation: independent\n---\nMy synthesis.\n", encoding="utf-8",
    )
    assert "unmanifested_document" in _codes(run_gate("research", researched, researched.parent.parent))


def test_vendor_page_cannot_be_independent(run: Path, server, monkeypatch) -> None:
    monkeypatch.setattr(gate, "MIN_RESEARCH_DOMAINS", 2)
    for i, p in enumerate(("/a", "/b", "/c", "/d", "/e")):
        _fetch(run, server[i % 2] + p, st="vendor_page" if p == "/e" else "news_web")
    _plan(run)
    assert "vendor_page_not_vendor" in _codes(run_gate("research", run, run.parent.parent))


def test_every_document_answers_a_question(researched: Path) -> None:
    plan = json.loads((researched / "research.json").read_text())
    plan["sources"] = plan["sources"][1:]
    plan["sources"][0]["question"] = "A question the plan never asked?"
    (researched / "research.json").write_text(json.dumps(plan), encoding="utf-8")
    codes = _codes(run_gate("research", researched, researched.parent.parent))
    assert "unexplained_document" in codes and "source_answers_no_question" in codes


def test_company_blog_marked_independent_warns(researched: Path, monkeypatch) -> None:
    manifest_path = researched / "corpus" / "_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    first = sorted(manifest)[0]
    manifest[first]["url"] = "https://vendor.example/blog/why-you-need-us"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    rpt = run_gate("research", researched, researched.parent.parent)
    assert rpt.passed
    assert "self_published_marked_independent" in [w.code for w in rpt.warnings]


def test_needs_enough_sites(researched: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "MIN_RESEARCH_DOMAINS", 3)
    assert "too_few_domains" in _codes(run_gate("research", researched, researched.parent.parent))


def test_evidence_waits_for_research(researched: Path) -> None:
    (researched / "evidence.json").write_text(json.dumps({"corpus": "runs/r/corpus", "claims": []}), encoding="utf-8")
    rpt = run_gate("evidence", researched, researched.parent.parent)
    assert _codes(rpt) == ["upstream_not_passed"]


def test_hook_blocks_agent_writes_to_the_corpus(researched: Path) -> None:
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(researched / "corpus" / "01-anything.md")},
    }
    r = subprocess.run(
        [sys.executable, "-m", "kaizen", "hook"],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert r.returncode == 2
    assert "research corpus" in r.stderr
