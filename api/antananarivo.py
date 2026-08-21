"""Scraper des résultats du BAC publiés par l'Université d'Antananarivo.

La page est une application React. Les résultats sont actuellement embarqués dans
le bundle JavaScript sous la forme d'une constante minifiée (``const Qm=[...]``),
mais le scraper accepte aussi un tableau HTML rendu directement par la page.
"""

from __future__ import annotations

import ast
import json
import re
import time
import unicodedata
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import requests


SOURCE_URL = "https://www.univ-antananarivo.mg/resultats-bac"
DEFAULT_YEAR = "2026"
CACHE_TTL_SECONDS = 300

_CACHE: dict[str, Any] = {"expires_at": 0.0, "results": None}


class _ResultTableParser(HTMLParser):
    """Extrait les cellules des tableaux HTML sans dépendance externe."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._table_depth = 0
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth += 1
        elif self._table_depth and tag == "tr":
            self._row = []
        elif self._row is not None and tag in {"td", "th"}:
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._cell_parts is not None and tag in {"td", "th"}:
            self._row.append(" ".join("".join(self._cell_parts).split()))
            self._cell_parts = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)


def _normalize_text(value: Any) -> str:
    """Normalise un texte pour les recherches insensibles aux accents et à la casse."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFD", str(value))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.strip().casefold().split())


def _first_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and value != "":
            return value
    return None


def normalize_result(record: dict[str, Any], default_year: str = DEFAULT_YEAR) -> dict[str, Any]:
    """Convertit un enregistrement UA vers le contrat commun de l'API."""
    matricule = _first_value(record, "matricule", "numeroInscription", "numero", "num", "registrationNumber")
    nom = _first_value(record, "nom", "name", "lastName", "lastname")
    prenoms = _first_value(record, "prenoms", "prénoms", "prenom", "firstName", "firstname")
    fullname_source = _first_value(record, "fullname", "fullName")
    observation = _first_value(record, "observation", "resultat", "result", "status")
    mention = _first_value(record, "mention", "grade")
    serie = _first_value(record, "serie", "série", "series")
    centre = _first_value(record, "center", "centre", "centreExamen")
    annee = _first_value(record, "annee", "année", "year") or default_year

    nom_text = str(nom or "").strip()
    prenoms_text = str(prenoms or "").strip()
    fullname = " ".join(part for part in (nom_text, prenoms_text) if part).strip()
    if not fullname and fullname_source:
        fullname = str(fullname_source).strip()
    observation_text = str(observation or "").strip()
    observation_normalized = _normalize_text(observation_text)
    admis = 1 if (
        observation_normalized in {"vrai", "true", "admis", "admis(e)"}
        or ("admis" in observation_normalized and "non" not in observation_normalized)
    ) else 0

    return {
        "matricule": str(matricule).strip() if matricule is not None else None,
        "fullname": fullname,
        "nom": nom_text or None,
        "prenoms": prenoms_text or None,
        "serie": str(serie).strip() if serie is not None else None,
        "mention": str(mention).strip() if mention is not None else None,
        "center": str(centre).strip() if centre is not None else None,
        "observation": observation_text or None,
        "annee": str(annee).strip(),
        "admis": admis,
        "admis_label": "Admis(e)" if admis else "Non admis(e)",
    }


def _extract_balanced_array(text: str, opening_index: int) -> str | None:
    """Retourne un littéral JavaScript ``[...]`` en respectant les chaînes."""
    if opening_index >= len(text) or text[opening_index] != "[":
        return None

    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(opening_index, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[opening_index : index + 1]
    return None


def _parse_js_array(literal: str) -> list[dict[str, Any]] | None:
    """Parse un tableau JSON ou un littéral d'objet JavaScript simple."""
    try:
        parsed = json.loads(literal)
    except (TypeError, json.JSONDecodeError):
        normalized = re.sub(
            r"(?<![\"'])\b([A-Za-z_$][\w$]*)\s*:",
            r"'\1':",
            literal,
        )
        normalized = re.sub(r"\btrue\b", "True", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bfalse\b", "False", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bnull\b|\bundefined\b", "None", normalized)
        normalized = re.sub(r",\s*([}\]])", r"\1", normalized)
        try:
            parsed = ast.literal_eval(normalized)
        except (SyntaxError, ValueError, TypeError):
            return None

    if not isinstance(parsed, list):
        return None
    return [item for item in parsed if isinstance(item, dict)]


def parse_embedded_results(script_text: str) -> list[dict[str, Any]] | None:
    """Extrait la constante de résultats du bundle compilé de l'Université."""
    # Le nom ``Qm`` est celui observé dans le bundle actuel. Le second motif
    # permet de continuer à fonctionner si le minifieur renomme cette constante.
    preferred = re.search(r"\bconst\s+Qm\s*=\s*\[", script_text)
    candidate_positions = [preferred.end() - 1] if preferred else []

    if not candidate_positions:
        for match in re.finditer(r"\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*\[", script_text):
            literal = _extract_balanced_array(script_text, match.end() - 1)
            if literal and any(key in literal for key in ("matricule", "numeroInscription")):
                candidate_positions.append(match.end() - 1)
                break

    for position in candidate_positions:
        literal = _extract_balanced_array(script_text, position)
        if literal is None:
            return None
        parsed = _parse_js_array(literal)
        if parsed is not None:
            return parsed
    return None


def _rows_to_results(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Convertit les colonnes du tableau UA en enregistrements normalisés."""
    if not rows:
        return []

    headers = [_normalize_text(value).replace("'", "") for value in rows[0]]
    has_header = any("inscription" in header or header in {"nom", "prenoms", "prénoms"} for header in headers)
    data_rows = rows[1:] if has_header else rows

    if has_header:
        key_by_header = {
            "numero dinscription": "matricule",
            "numero inscription": "matricule",
            "matricule": "matricule",
            "nom": "nom",
            "prenoms": "prenoms",
            "prénoms": "prenoms",
            "observation": "observation",
            "mention": "mention",
            "serie": "serie",
            "série": "serie",
            "annee": "annee",
            "année": "annee",
        }
        keys = [key_by_header.get(header, "") for header in headers]
    else:
        keys = ["matricule", "nom", "prenoms", "observation", "mention", "serie"]

    results: list[dict[str, Any]] = []
    for row in data_rows:
        if not any(cell.strip() for cell in row):
            continue
        record = {keys[index]: cell for index, cell in enumerate(row) if index < len(keys) and keys[index]}
        if record.get("matricule") or record.get("nom") or record.get("prenoms"):
            results.append(record)
    return results


def parse_html_results(page_html: str) -> list[dict[str, Any]]:
    """Extrait un tableau de résultats si la page est rendue côté serveur."""
    parser = _ResultTableParser()
    parser.feed(page_html)
    return _rows_to_results(parser.rows)


def _script_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    for match in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", page_html, flags=re.IGNORECASE):
        url = urljoin(SOURCE_URL, match.group(1))
        if url not in urls:
            urls.append(url)
    return urls


def _cache_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _CACHE["results"] = results
    _CACHE["expires_at"] = time.time() + CACHE_TTL_SECONDS
    return results


def scrape_results(http_session: requests.Session, force_refresh: bool = False) -> dict[str, Any]:
    """Télécharge et extrait les résultats actuellement publiés par la source UA."""
    if not force_refresh and _CACHE["results"] is not None and time.time() < _CACHE["expires_at"]:
        return {
            "status": "OK",
            "results": _CACHE["results"],
            "source_message": "Aucun résultat publié sur la source." if not _CACHE["results"] else None,
            "cached": True,
        }

    try:
        page_response = http_session.get(SOURCE_URL, timeout=(10, 45))
        page_response.raise_for_status()
        page_html = page_response.text

        raw_results = parse_html_results(page_html)
        if not raw_results:
            inline_scripts = re.findall(r"<script(?![^>]+src=)[^>]*>(.*?)</script>", page_html, flags=re.IGNORECASE | re.DOTALL)
            for inline_script in inline_scripts:
                raw_results = parse_embedded_results(inline_script) or []
                if raw_results:
                    break

        if not raw_results:
            for script_url in _script_urls(page_html):
                script_response = http_session.get(script_url, timeout=(10, 90))
                script_response.raise_for_status()
                parsed = parse_embedded_results(script_response.text)
                if parsed is not None:
                    raw_results = parsed
                    break

        normalized_results = [normalize_result(record) for record in raw_results]
        _cache_results(normalized_results)
        return {
            "status": "OK",
            "results": normalized_results,
            "source_message": "Aucun résultat publié sur la source." if not normalized_results else None,
            "cached": False,
        }
    except requests.exceptions.Timeout:
        return {"status": "ERROR", "error": "Timeout - La page de l'Université d'Antananarivo ne répond pas"}
    except requests.exceptions.ConnectionError:
        return {"status": "ERROR", "error": "Impossible de se connecter à la page de l'Université d'Antananarivo"}
    except requests.exceptions.HTTPError as error:
        return {"status": "ERROR", "error": f"Erreur HTTP {error.response.status_code}"}
    except Exception as error:  # pragma: no cover - filet de sécurité pour la source distante
        return {"status": "ERROR", "error": f"Erreur de scraping Antananarivo: {error}"}


def search_results(
    http_session: requests.Session,
    search_term: str,
    mode: str = "nom",
    annee: str | None = None,
) -> dict[str, Any]:
    """Scrape puis filtre les résultats UA par matricule, nom/prénoms et année."""
    scraped = scrape_results(http_session)
    if scraped.get("status") != "OK":
        return scraped

    normalized_term = _normalize_text(search_term)
    normalized_year = _normalize_text(annee) if annee else ""
    filtered: list[dict[str, Any]] = []

    for candidate in scraped.get("results", []):
        if normalized_year and _normalize_text(candidate.get("annee")) != normalized_year:
            continue
        if mode == "matricule":
            haystack = _normalize_text(candidate.get("matricule"))
        else:
            haystack = _normalize_text(
                " ".join(
                    value for value in (
                        candidate.get("fullname"),
                        candidate.get("nom"),
                        candidate.get("prenoms"),
                    )
                    if value
                )
            )
        if normalized_term in haystack:
            filtered.append(candidate)

    return {
        "status": "OK",
        "province": "antananarivo",
        "mode": mode,
        "search_term": search_term,
        "annee": annee,
        "count": len(filtered),
        "results": filtered,
        "source_message": scraped.get("source_message"),
        "source_url": SOURCE_URL,
    }


def clear_cache() -> None:
    """Vide le cache, utile pour les tests et pour forcer une actualisation."""
    _CACHE["results"] = None
    _CACHE["expires_at"] = 0.0
