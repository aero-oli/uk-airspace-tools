from __future__ import annotations

from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .base import AirspaceFeature, AirspaceProvider
from ..parsers.notam import parse_notams_from_xml


DEFAULT_NATS_PIB_URL = "https://www.nats.aero/do-it-online/pre-flight-information-bulletins/"


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.links.append(href)


class NatsPibXmlProvider(AirspaceProvider):
    provider_id = "nats_pib_xml"
    display_name = "NATS PIB XML"

    def __init__(self, url: str = DEFAULT_NATS_PIB_URL, timeout: int = 30):
        self.url = url or DEFAULT_NATS_PIB_URL
        self.timeout = timeout
        self.resolved_url: str | None = None
        self.content_type: str | None = None

    def fetch(self) -> bytes:
        raw, content_type, final_url = self._download(self.url)
        self.content_type = content_type
        self.resolved_url = final_url

        if self._looks_like_xml(raw, content_type, final_url):
            return raw

        html = raw.decode("utf-8", errors="replace")
        candidate_urls = self._find_xml_candidates(html, final_url)
        errors = []
        for candidate in candidate_urls:
            try:
                candidate_raw, candidate_type, candidate_final = self._download(candidate)
                if self._looks_like_xml(candidate_raw, candidate_type, candidate_final):
                    self.content_type = candidate_type
                    self.resolved_url = candidate_final
                    return candidate_raw
            except (RuntimeError, HTTPError, URLError, TimeoutError, OSError) as exc:
                errors.append(f"{candidate}: {exc}")

        detail = "; ".join(errors) if errors else "No likely XML links were found on the page."
        raise RuntimeError(f"Could not locate a NOTAM PIB XML file from {self.url}. {detail}")

    def parse(self, raw: bytes) -> list[AirspaceFeature]:
        return parse_notams_from_xml(raw, source=self.display_name, source_url=self.resolved_url or self.url)

    def source_metadata(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "display_name": self.display_name,
            "configured_url": self.url,
            "resolved_url": self.resolved_url,
            "content_type": self.content_type,
        }

    def _download(self, url: str) -> tuple[bytes, str | None, str]:
        request = Request(url, headers={"User-Agent": "UKAirspaceTools-QGIS/0.1"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read(), response.headers.get("content-type"), response.geturl()
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"Could not fetch {url}: {exc}") from exc

    @staticmethod
    def _looks_like_xml(raw: bytes, content_type: str | None, url: str) -> bool:
        head = raw[:200].lstrip().lower()
        return (
            "xml" in (content_type or "").lower()
            or url.lower().split("?", 1)[0].endswith(".xml")
            or head.startswith(b"<?xml")
            or head.startswith(b"<notam")
            or head.startswith(b"<")
            and b"notam" in raw[:2000].lower()
            and b"<html" not in raw[:500].lower()
        )

    @staticmethod
    def _find_xml_candidates(html: str, base_url: str) -> list[str]:
        parser = _LinkParser()
        parser.feed(html)
        ranked: list[tuple[int, str]] = []
        for href in parser.links:
            absolute = urljoin(base_url, href)
            lower = absolute.lower()
            score = 0
            if ".xml" in lower:
                score += 100
            if "pib" in lower:
                score += 25
            if "notam" in lower:
                score += 25
            if "pre-flight" in lower or "brief" in lower:
                score += 10
            if score:
                ranked.append((score, absolute))
        ranked.sort(reverse=True, key=lambda item: item[0])
        seen = set()
        results = []
        for _, url in ranked:
            if url not in seen:
                seen.add(url)
                results.append(url)
        return results
