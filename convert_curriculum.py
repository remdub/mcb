#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11,<3.13"
# dependencies = [
#     "marker-pdf>=2.0.0",
#     "pyyaml>=6.0",
#     "rich>=13.7.0",
# ]
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
# torchvision = { index = "pytorch-cpu" }
# ///
"""
convert_curriculum.py
=====================
Universal pipeline to convert ANY curriculum PDF (CPEONS, FWB, SEGEC, WBE, etc.)
into AI-agent-optimized Markdown using Marker (`marker-pdf`) and UV.

Key Capabilities:
- 100% Dynamic Discovery: Automatically discovers all curriculum units (UAA, Unité,
  Module, Chapitre), learning situations, timetable grids, and pedagogical guidelines.
  No hardcoded unit list required!
- Metadata Extraction: Automatically parses unit numbers, titles, grade years,
  degree cycles, period/hour volumes, themes, competencies, and prerequisites.
- Automatic Graph Linking: Computes bidirectional relationships (prerequisites and leads_to)
  across all units automatically.
- Device Auto-Detection: Automatically detects CUDA vs CPU with memory safety.
- Two-Tier Caching: Caches raw Marker extraction in `.cache/raw_marker.md` so splitting,
  metadata refinement, and formatting run in under 2 seconds via `--skip-marker`.
- Dual-Anchor Boundary Precision: Aligns section headers and competence blocks to eliminate
  inter-page table bleeding.
- Optional Catalog Overrides: Accepts an optional external JSON/YAML catalog for custom
  metadata overrides when desired (`--catalog-file`).
- Agent Manifest Generation: Produces `00_AGENT_MANIFEST.md` and `agent_manifest.json`
  optimized for LLM agent tool-calling, RAG indexing, and context-window efficiency.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SectionItem:
    key: str
    title: str
    doc_type: str
    content: str
    rel_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Device Detection & Text Cleaning
# ---------------------------------------------------------------------------

def detect_device(requested: str = "auto") -> str:
    """Resolve compute device safely."""
    if requested in ("cpu", "cuda"):
        return requested
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def clean_markdown_text(text: str) -> str:
    """
    Sanitize raw Marker output by stripping repetitive curriculum headers,
    footers, page numbering, HTML span anchors, and normalizing whitespace.
    """
    # 1. Normalize form-feeds, non-breaking spaces, and page span anchors
    text = text.replace("\x0c", "\n\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r'<span id="page-[^"]*"></span>', "", text)

    # 2. Normalize <sup>e</sup> tags to plain text
    text = re.sub(r"<sup>(.*?)</sup>", r"\1", text)

    # 3. Strip running footer lines commonly found in curriculum documents
    # (e.g. "CPEONS – Programme enseignement secondaire...", "FWB - ...", etc.)
    text = re.sub(
        r"(?:CPEONS|FWB|SEGEC|WBE)\s*–\s*Programme[^\n]*\n?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 4. Strip standalone page numbers (lines containing just 1-3 digits)
    text = re.sub(r"\n\s*\d{1,3}\s*\n", "\n\n", text)

    # 5. Clean table of contents dots noise (. . . . . . 24)
    text = re.sub(r"\.{4,}\s*\d+", "", text)

    # 6. Collapse excessive empty newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 7. Normalize heading order: if unit header appears after the initial Compétence block
    # due to multi-column reading order in the PDF layout, swap them so the unit starts cleanly.
    def _swap_comp_and_unit(m: re.Match) -> str:
        comp_part = m.group(1).strip()
        unit_part = m.group(2).strip()
        return f"\n\n{unit_part}\n\n{comp_part}\n\n"

    unit_misorder_pattern = re.compile(
        r"(#{1,4}\s*\*\*Compétences?\s*:?[\s\S]{1,600}?)(#{0,4}\s*\*{0,2}\s*(?:UAA|Unité|Module|Chapitre)\s*\d{1,2}\s*:\s*[^\n]+)",
        re.IGNORECASE,
    )
    text = unit_misorder_pattern.sub(_swap_comp_and_unit, text)

    # 8. Normalize Grilles Horaires heading position if table precedes it:
    def _swap_grilles_table(m: re.Match) -> str:
        tbl = m.group(1).strip()
        hdr = m.group(2).strip()
        return f"\n\n{hdr}\n\n{tbl}\n\n"

    grilles_misorder_pattern = re.compile(
        r"((?:\|[^\n]+\|\n)+)\s*(#{1,4}\s*\*{0,2}GRILLES?\s*HORAIRES?[^\n]*)",
        re.IGNORECASE,
    )
    text = grilles_misorder_pattern.sub(_swap_grilles_table, text)

    return text.strip()


def extract_document_title(text: str, default_name: str) -> str:
    """Extract a meaningful curriculum document title, avoiding metadata/acknowledgements."""
    # 1. Search for explicit "Programme de..." or "Programme d'études..." or "Référentiel..." in the first 40 lines
    lines = text.split("\n", 40)[:40]
    for line in lines:
        cleaned_line = re.sub(r"^[#*_\s]+|[#*_\s]+$", "", line).strip()
        if re.search(r"^(?:Programme\s+de|Programme\s+d['’]|Référentiel\s+de|Profil\s+de)\b", cleaned_line, re.IGNORECASE):
            return cleaned_line

    # 2. Search for the first markdown heading that is NOT an administrative header
    blacklist = {"remerciements", "table des matières", "sommaire", "table des matieres", "introduction", "avant-propos"}
    for m in re.finditer(r"^\s*#+\s*([^\n]+)", text, re.MULTILINE):
        candidate = m.group(1).strip(" *#")
        if candidate.lower() not in blacklist and len(candidate) > 3:
            return candidate

    return default_name


def sanitize_filename(name: str) -> str:
    """Turn any title string into a safe lower snake_case filename segment."""
    s = name.lower()
    s = re.sub(r"[àáâãäå]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôõö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s).strip("_")
    return s[:45]


# ---------------------------------------------------------------------------
# Dynamic Metadata Extraction
# ---------------------------------------------------------------------------

def extract_unit_metadata(
    chunk_text: str,
    unit_type: str,
    unit_num: int,
    raw_title: str,
    extra_header_info: str,
    catalog_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dynamically inspect a unit's text to infer its year, degree, periods,
    competencies, theme, prerequisites, and tags without any hardcoding.
    """
    # 1. Clean Title
    title = raw_title.strip(" *#")
    title = re.sub(r"\\([*_-])", r"\1", title).strip()

    # 2. Year / Degree extraction
    year = ""
    degree = ""
    combined_header = f"{extra_header_info} {chunk_text[:1200]}"

    # Search for year (e.g. "3e année", "4e année", "5e", "6e")
    year_match = re.search(r"(\d{1,2})\s*e?\s*année", combined_header, re.IGNORECASE)
    if year_match:
        year = f"{year_match.group(1)}e année"
    else:
        # Fallback search for degree
        deg_match = re.search(r"(?:degré\s*(\d)|D(\d))", combined_header, re.IGNORECASE)
        if deg_match:
            deg_num = deg_match.group(1) or deg_match.group(2)
            degree = f"D{deg_num}"

    # Infer degree from year if not set
    if year and not degree:
        if any(y in year for y in ("1e", "2e", "1re")):
            degree = "D1"
        elif any(y in year for y in ("3e", "4e")):
            degree = "D2"
        elif any(y in year for y in ("5e", "6e", "7e")):
            degree = "D3"

    # 3. Period / Hour volume extraction
    periods = ""
    period_match = re.search(
        r"(?:de\s+)?(\d+(?:\s*à\s*\d+)?)\s*(?:périodes?|heures?|h\b)",
        extra_header_info,
        re.IGNORECASE,
    )
    if period_match:
        periods = period_match.group(0).strip(" ()")
    else:
        # Search in top of chunk
        period_match2 = re.search(
            r"\(DE\s*(\d+(?:\s*À\s*\d+)?)\s*PÉRIODES?\)",
            chunk_text[:500],
            re.IGNORECASE,
        )
        if period_match2:
            periods = period_match2.group(1).strip() + " périodes"

    # 4. Competency extraction
    comp_match = re.search(
        r"#{1,4}\s*\*{0,2}\s*Compétences?\s*:?\*?\*?\s*\n+([^#\n|]+(?:\n[^#\n|]+)*)",
        chunk_text,
        re.IGNORECASE,
    )
    competency = ""
    if comp_match:
        competency = comp_match.group(1).strip()
        competency = re.sub(r"^[•\-\*]\s*", "", competency).strip()
        # Clean multiline whitespace
        competency = re.sub(r"\s+", " ", competency)

    # 5. Theme / Subject domain extraction
    theme = ""
    theme_match = re.search(
        r"(?:appartient|fait partie|relève|thématique|thème)\s+(?:du|au|de la)?\s*(?:thème\s+)?[\"«“]([^\"»”]+)[\"»”]",
        chunk_text[:2000],
        re.IGNORECASE,
    )
    if theme_match:
        theme = theme_match.group(1).strip()
    else:
        # Fallback to title keywords
        theme = title.split()[0] if title else "Général"

    # 6. Prerequisites extraction
    prereqs = []
    # Look for prerequisite lines
    for line in chunk_text[:3000].split("\n"):
        if re.search(r"prérequis|prerequis", line, re.IGNORECASE):
            found = re.findall(rf"(?:{unit_type})\s*(\d{{1,2}})", line, re.IGNORECASE)
            for f_num in found:
                p_int = int(f_num)
                if p_int != unit_num:  # Avoid self-reference
                    prereqs.append(f"{unit_type.upper()} {p_int}")

    prereqs = list(dict.fromkeys(prereqs))  # Deduplicate preserving order

    # 7. Summary generation
    summary = ""
    if competency:
        summary = competency[:250] + ("..." if len(competency) > 250 else "")
    else:
        # First informative paragraph
        for p in chunk_text.split("\n\n"):
            p_strip = p.strip()
            if len(p_strip) > 50 and not p_strip.startswith(("#", "|", "---")):
                summary = re.sub(r"\s+", " ", p_strip)[:250]
                break

    # 8. Dynamic tags
    tag_candidates = set()
    tag_candidates.add(unit_type.lower())
    if theme:
        tag_candidates.add(theme.lower())
    for word in re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", title.lower()):
        if word not in ("pour", "avec", "dans", "cette", "vers", "sans", "dont"):
            tag_candidates.add(word)

    unit_key = f"{unit_type.lower()}_{unit_num:02d}"
    meta: Dict[str, Any] = {
        "id": unit_key,
        "number": unit_num,
        "title": title,
        "degree": degree or "N/A",
        "year": year or "N/A",
        "periods": periods or "N/A",
        "theme": theme or "Général",
        "prerequisites": prereqs,
        "leads_to": [],  # Will be populated in graph resolution pass
        "tags": sorted(list(tag_candidates)),
        "summary": summary or f"Unité {unit_num} : {title}.",
    }

    # Apply external catalog overrides if provided
    if catalog_override and unit_key in catalog_override:
        meta.update(catalog_override[unit_key])

    return meta


# ---------------------------------------------------------------------------
# Universal Semantic Splitter
# ---------------------------------------------------------------------------

def split_curriculum_markdown(
    full_text: str,
    unit_prefixes: Tuple[str, ...] = ("UAA", "Unité", "Module", "Chapitre"),
    catalog_overrides: Optional[Dict[str, Any]] = None,
) -> List[SectionItem]:
    """
    Dynamically discover all units and sections in any curriculum text,
    calculate dual-anchor boundaries, and construct modular section objects.
    """
    sections: List[SectionItem] = []
    prefix_regex = "|".join(re.escape(p) for p in unit_prefixes)

    # 1. Regex patterns
    unit_header_pattern = re.compile(
        rf"(?:^|\n)\s*#{{0,4}}\s*\*{{0,2}}\s*(({prefix_regex})\s*(\d{{1,2}})\s*:\s*([^–—\n]+)(?:[–—\-]\s*([^\n]+))?)",
        re.IGNORECASE,
    )

    sit_pattern = re.compile(
        r"#\s*(?:<span[^>]*></span>\s*)?(?:EXEMPLE DE )?SITUATION D['’]APPRENTISSAGE",
        re.IGNORECASE,
    )

    pedago_pattern = re.compile(
        r"(?:^|\n)\s*#{1,2}\s*\*{0,2}\s*(CONSIDÉRATIONS PÉDAGOGIQUES[^\n]*)",
        re.IGNORECASE,
    )

    glossary_pattern = re.compile(
        r"(?:^|\n)\s*#{1,2}\s*\*{0,2}\s*(GLOSSAIRE[^\n]*|LEXIQUE[^\n]*)",
        re.IGNORECASE,
    )

    biblio_pattern = re.compile(
        r"(?:^|\n)\s*#{1,2}\s*\*{0,2}\s*(BIBLIOGRAPHIE[^\n]*)",
        re.IGNORECASE,
    )

    horaires_pattern = re.compile(
        r"(?:^|\n)\s*#{1,4}\s*\*{0,2}\s*(GRILLES?\s*HORAIRES?[^\n]*|RÉPARTITION\s*HORAIRE[^\n]*)",
        re.IGNORECASE,
    )

    # 2. Competence anchors
    comps = list(re.finditer(r"(?:^|\n)\s*#{1,4}\s*\*{0,2}\s*Compétences?\s*:?", full_text, re.IGNORECASE))
    comp_matches: List[Tuple[str, int, int]] = []
    for c in comps:
        snippet = full_text[c.start():c.start() + 700]
        m_num = re.search(rf"({prefix_regex})\s*(\d{{1,2}})(?!\s*(?:e|ère|eme|ème)?\s*année)\b", snippet, re.IGNORECASE)
        if m_num:
            comp_matches.append((m_num.group(1).upper(), int(m_num.group(2)), c.start()))

    # 3. Discovered unit headers
    header_matches: List[Tuple[str, int, int, str, str]] = []
    for m in unit_header_pattern.finditer(full_text):
        if "|" in m.group(0) or "...." in m.group(0):
            continue  # Skip table of contents references
        pfx = m.group(2).upper()
        num = int(m.group(3).strip())
        raw_title = m.group(4).strip(" *#")
        extra = m.group(5).strip(" *#") if m.group(5) else ""
        header_matches.append((pfx, num, m.start(), raw_title, extra))

    # 4. Intro theme anchors: L'UAA X (appartient|fait partie|...)
    intro_pat = re.compile(rf"(?:^|\n)\s*L[\'’]({prefix_regex})\s*(\d{{1,2}})\b", re.IGNORECASE)
    intro_matches: List[Tuple[str, int, int]] = []
    for m in intro_pat.finditer(full_text):
        intro_matches.append((m.group(1).upper(), int(m.group(2)), m.start()))

    # 5. Consolidate unit start anchors monotonically
    unique_units = sorted(
        list(set([(p, n) for p, n, _ in comp_matches] + [(p, n) for p, n, _, _, _ in header_matches])),
        key=lambda x: x[1]
    )

    markers: List[Dict[str, Any]] = []
    last_unit_pos = 0

    for pfx, num in unique_units:
        cands: List[int] = []
        for p, n, pos in comp_matches:
            if p == pfx and n == num and pos > last_unit_pos:
                cands.append(pos)
        h_title = ""
        h_extra = ""
        for p, n, pos, t, e in header_matches:
            if p == pfx and n == num:
                h_title = t
                h_extra = e
                if pos > last_unit_pos:
                    cands.append(pos)
        for p, n, pos in intro_matches:
            if p == pfx and n == num and pos > last_unit_pos:
                cands.append(pos)

        if cands:
            start_pos = min(cands)
            last_unit_pos = start_pos
            markers.append({
                "pos": start_pos,
                "type": "unit",
                "prefix": pfx,
                "number": num,
                "raw_title": h_title or f"{pfx} {num}",
                "extra": h_extra,
            })

    # Add Grilles Horaires
    for m in horaires_pattern.finditer(full_text):
        if "|" not in m.group(0) and "...." not in m.group(0):
            markers.append({"pos": m.start(), "type": "horaires", "title": m.group(1).strip(" *#")})
            break

    # Add Situations d'apprentissage
    for m in sit_pattern.finditer(full_text):
        if "|" not in m.group(0) and "...." not in m.group(0):
            markers.append({"pos": m.start(), "type": "situation"})

    # Post-unit sections (Pedagogie, Glossaire, Bibliographie & Annexes)
    end_of_units = max(m["pos"] for m in markers if m["type"] == "unit") if markers else 0
    post_text = full_text[end_of_units:]

    m_ped = pedago_pattern.search(post_text)
    if m_ped:
        markers.append({"pos": end_of_units + m_ped.start(), "type": "pedagogie", "title": m_ped.group(1).strip(" *#")})

    m_glo = glossary_pattern.search(post_text)
    if m_glo:
        markers.append({"pos": end_of_units + m_glo.start(), "type": "glossaire", "title": m_glo.group(1).strip(" *#")})

    m_bib = biblio_pattern.search(post_text)
    if m_bib:
        markers.append({"pos": end_of_units + m_bib.start(), "type": "biblio", "title": m_bib.group(1).strip(" *#")})

    # Sort markers chronologically
    markers.sort(key=lambda x: x["pos"])

    # 5. Extract Initial Introduction / Cadre général
    first_split_pos = markers[0]["pos"] if markers else len(full_text)
    cadre_text = full_text[:first_split_pos].strip()
    sections.append(
        SectionItem(
            key="01_cadre_general_et_profil",
            title="Cadre général et profil de formation",
            doc_type="cadre",
            content=cadre_text,
            rel_path="01_cadre_general_et_profil.md",
            metadata={
                "id": "cadre_general",
                "title": "Cadre général et profil de formation",
                "type": "cadre",
                "tags": ["référentiel", "profil de formation", "objectifs pédagogiques"],
                "summary": "Présentation institutionnelle, fondements décrétaux, profil de formation et thématiques générales.",
            },
        )
    )

    # 6. Iterate through content markers to carve out chunks
    sit_counter = 1
    unit_metadata_list: List[Dict[str, Any]] = []

    for i, curr in enumerate(markers):
        start_pos = curr["pos"]
        end_pos = markers[i + 1]["pos"] if i + 1 < len(markers) else len(full_text)
        chunk_text = full_text[start_pos:end_pos].strip()

        m_type = curr["type"]

        if m_type == "horaires":
            sections.append(
                SectionItem(
                    key="02_grilles_horaires",
                    title="Grilles horaires de la formation",
                    doc_type="grille_horaire",
                    content=chunk_text,
                    rel_path="02_grilles_horaires.md",
                    metadata={
                        "id": "grilles_horaires",
                        "title": "Grilles horaires de la formation",
                        "type": "horaires",
                        "tags": ["grilles horaires", "volume horaire", "périodes"],
                        "summary": "Répartition hebdomadaire et annuelle des périodes de cours par année d'études.",
                    },
                )
            )

        elif m_type == "unit":
            pfx = curr["prefix"]
            num = curr["number"]
            raw_title = curr["raw_title"]
            extra = curr["extra"]

            unit_meta = extract_unit_metadata(
                chunk_text=chunk_text,
                unit_type=pfx,
                unit_num=num,
                raw_title=raw_title,
                extra_header_info=extra,
                catalog_override=catalog_overrides,
            )
            unit_metadata_list.append(unit_meta)

            unit_key = unit_meta["id"]
            safe_title = sanitize_filename(unit_meta["title"])
            dir_name = pfx.lower()
            rel_path = f"{dir_name}/{unit_key}_{safe_title}.md"

            sections.append(
                SectionItem(
                    key=unit_key,
                    title=f"{pfx} {num} : {unit_meta['title']}",
                    doc_type="uaa",
                    content=chunk_text,
                    rel_path=rel_path,
                    metadata=unit_meta,
                )
            )

        elif m_type == "situation":
            sit_key = f"situation_{sit_counter:02d}"
            # Extract clean title:
            sit_subtitle = ""
            for h in re.finditer(r"#{2,4}\s*\*{0,2}([^\n*#]+)\*{0,2}", chunk_text[:800]):
                line_t = h.group(1).strip()
                if not re.search(r"documents fournis|consignes|attitudes|savoir-faire|commentaires", line_t, re.IGNORECASE):
                    sit_subtitle = line_t
                    break
            if not sit_subtitle:
                m_consigne = re.search(r"(?:On te propose de|Il t['’]est demandé de|Pour répondre à|Un client demande)\s+([^.\n]+)", chunk_text[:1500])
                if m_consigne:
                    sit_subtitle = m_consigne.group(0).strip()
            if not sit_subtitle:
                for l in chunk_text.splitlines()[1:]:
                    l_s = l.strip(" #*-o●")
                    if len(l_s) > 10 and not re.search(r"documents|consignes|attitudes", l_s, re.IGNORECASE):
                        sit_subtitle = l_s[:60]
                        break
            if not sit_subtitle:
                sit_subtitle = f"Situation {sit_counter}"

            clean_sub = re.sub(r"^[•\-\*]\s*", "", sit_subtitle)[:70].strip()

            sections.append(
                SectionItem(
                    key=sit_key,
                    title=f"Situation d'apprentissage {sit_counter} : {clean_sub}",
                    doc_type="situation_apprentissage",
                    content=chunk_text,
                    rel_path=f"situations_apprentissage/{sit_key}_{sanitize_filename(clean_sub)}.md",
                    metadata={
                        "id": sit_key,
                        "title": clean_sub,
                        "type": "situation_apprentissage",
                        "index": sit_counter,
                        "tags": ["situation d'apprentissage", "projet pratique", "pédagogie active"],
                        "summary": f"Exemple guidé d'apprentissage pratique et mise en situation concrète ({clean_sub}).",
                    },
                )
            )
            sit_counter += 1

        elif m_type == "pedagogie":
            sections.append(
                SectionItem(
                    key="03_considerations_pedagogiques",
                    title="Considérations pédagogiques, méthodologie et évaluation",
                    doc_type="pedagogie",
                    content=chunk_text,
                    rel_path="03_considerations_pedagogiques_et_evaluation.md",
                    metadata={
                        "id": "pedagogie_evaluation",
                        "title": "Considérations pédagogiques et modalités d'évaluation",
                        "type": "pedagogie",
                        "tags": ["méthodologie", "évaluation", "remédiation", "posture enseignante"],
                        "summary": "Recommandations méthodologiques, posture de l'enseignant et critères d'évaluation.",
                    },
                )
            )

        elif m_type == "glossaire":
            sections.append(
                SectionItem(
                    key="04_glossaire",
                    title="Glossaire des termes techniques",
                    doc_type="glossaire",
                    content=chunk_text,
                    rel_path="04_glossaire.md",
                    metadata={
                        "id": "glossaire",
                        "title": "Glossaire des termes techniques",
                        "type": "glossaire",
                        "tags": ["glossaire", "définitions", "terminologie"],
                        "summary": "Définitions des concepts clés et vocabulaire officiel employé dans le référentiel.",
                    },
                )
            )

        elif m_type == "biblio":
            sections.append(
                SectionItem(
                    key="05_bibliographie_et_annexes",
                    title="Bibliographie, sitographie et annexes",
                    doc_type="annexes",
                    content=chunk_text,
                    rel_path="05_bibliographie_et_annexes.md",
                    metadata={
                        "id": "bibliographie_annexes",
                        "title": "Bibliographie, sitographie et documents annexes",
                        "type": "annexes",
                        "tags": ["bibliographie", "sitographie", "annexes"],
                        "summary": "Ouvrages de référence, liens officiels et documents complémentaires.",
                    },
                )
            )

    # 7. Compute bidirectional prerequisite graph (leads_to)
    unit_map: Dict[str, SectionItem] = {
        s.metadata.get("id", "").upper(): s for s in sections if s.doc_type == "uaa"
    }

    for s in sections:
        if s.doc_type == "uaa":
            u_id = s.metadata.get("id", "").upper()
            prereqs = s.metadata.get("prerequisites", [])
            for p in prereqs:
                p_norm = p.replace(" ", "_").upper()
                if p_norm in unit_map:
                    target_meta = unit_map[p_norm].metadata
                    if u_id not in target_meta.get("leads_to", []):
                        target_meta.setdefault("leads_to", []).append(u_id)

    return sections


# ---------------------------------------------------------------------------
# Agent Optimization & Manifest Writer
# ---------------------------------------------------------------------------

def write_optimized_markdown(
    sections: List[SectionItem],
    out_dir: Path,
    source_pdf: str,
    doc_title: str,
) -> None:
    """
    Format each section with rich YAML frontmatter, add relative cross-links,
    and save into the target directory.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Filter units for cross-navigation
    unit_sections = [s for s in sections if s.doc_type == "uaa"]

    for s in sections:
        file_path = out_dir / s.rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        meta = {
            "source_document": Path(source_pdf).name,
            **s.metadata,
        }
        yaml_header = yaml.dump(meta, allow_unicode=True, sort_keys=False).strip()

        # Build relative navigation header
        nav_parts: List[str] = []
        if s.doc_type == "uaa":
            u_idx = unit_sections.index(s)
            prev_s = unit_sections[u_idx - 1] if u_idx > 0 else None
            next_s = unit_sections[u_idx + 1] if u_idx < len(unit_sections) - 1 else None

            if prev_s:
                rel_prev = os.path.relpath(out_dir / prev_s.rel_path, file_path.parent)
                nav_parts.append(f"[⬅ {prev_s.title}]({rel_prev})")
            nav_parts.append(f"[📑 Manifest Index]({os.path.relpath(out_dir / '00_AGENT_MANIFEST.md', file_path.parent)})")
            if next_s:
                rel_next = os.path.relpath(out_dir / next_s.rel_path, file_path.parent)
                nav_parts.append(f"[{next_s.title} ➡]({rel_next})")
        else:
            nav_parts.append(f"[📑 Manifest Index]({os.path.relpath(out_dir / '00_AGENT_MANIFEST.md', file_path.parent)})")

        nav_bar = " | ".join(nav_parts)

        md_body = (
            f"---\n{yaml_header}\n---\n\n"
            f"> {nav_bar}\n\n"
            f"# {s.title}\n\n"
            f"{s.content.strip()}\n\n"
            f"---\n> {nav_bar}\n"
        )

        file_path.write_text(md_body, encoding="utf-8")

    # Generate Manifests
    generate_agent_manifests(sections, out_dir, source_pdf, doc_title)


def generate_agent_manifests(
    sections: List[SectionItem],
    out_dir: Path,
    source_pdf: str,
    doc_title: str,
) -> None:
    """
    Generate 00_AGENT_MANIFEST.md and agent_manifest.json for AI agents and RAG engines.
    """
    manifest_data: Dict[str, Any] = {
        "curriculum_name": doc_title,
        "source_pdf": Path(source_pdf).name,
        "total_units": len([s for s in sections if s.doc_type == "uaa"]),
        "sections": [],
    }

    manifest_md_lines = [
        f"# Master Agent Manifest & Navigation Map - {doc_title}",
        "",
        "> **Notice for AI Agents**: This index provides high-level routing, prerequisites, and competency summaries.",
        "> Consult the specific modular `.md` files listed below rather than loading the whole document into context.",
        "",
        "## 🧭 Curriculum Progression & Learning Units",
        "",
        "| ID | Titre | Année / Degré | Périodes | Thème | Prérequis | Conduit à | Fichier Source |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for s in sections:
        item_entry = {
            "key": s.key,
            "title": s.title,
            "type": s.doc_type,
            "file": s.rel_path,
            "metadata": s.metadata,
        }
        manifest_data["sections"].append(item_entry)

        if s.doc_type == "uaa":
            meta = s.metadata
            prereqs = ", ".join(meta.get("prerequisites", [])) or "Aucun"
            leads = ", ".join(meta.get("leads_to", [])) or "-"
            year_deg = f"{meta.get('degree', '')} {meta.get('year', '')}".strip()
            manifest_md_lines.append(
                f"| **{meta.get('id', s.key).upper()}** | [{meta.get('title', s.title)}]({s.rel_path}) | {year_deg} | {meta.get('periods', '')} | {meta.get('theme', '')} | {prereqs} | {leads} | [`{s.rel_path}`]({s.rel_path}) |"
            )

    # Append learning situations
    manifest_md_lines.extend([
        "",
        "## 🛠️ Practical Learning Situations (Mises en situation)",
        "",
        "| Situation | Titre | Fichier |",
        "|---|---|---|",
    ])
    for s in sections:
        if s.doc_type == "situation_apprentissage":
            manifest_md_lines.append(f"| **{s.key}** | [{s.title}]({s.rel_path}) | [`{s.rel_path}`]({s.rel_path}) |")

    # Append general pedagogical & reference docs
    manifest_md_lines.extend([
        "",
        "## 📖 Framework, Methodology & References",
        "",
        "| Document | Description | Fichier |",
        "|---|---|---|",
    ])
    for s in sections:
        if s.doc_type not in ("uaa", "situation_apprentissage"):
            manifest_md_lines.append(f"| **{s.title}** | {s.metadata.get('summary', '')} | [`{s.rel_path}`]({s.rel_path}) |")

    # Write manifests
    (out_dir / "00_AGENT_MANIFEST.md").write_text("\n".join(manifest_md_lines) + "\n", encoding="utf-8")
    (out_dir / "agent_manifest.json").write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main Conversion Workflow
# ---------------------------------------------------------------------------

def run_conversion_pipeline(
    pdf_path: str,
    output_dir: Optional[str] = None,
    page_range: Optional[str] = None,
    mode: str = "fast",
    device: str = "auto",
    unit_prefixes: Tuple[str, ...] = ("UAA", "Unité", "Module", "Chapitre"),
    catalog_file: Optional[str] = None,
    skip_marker: bool = False,
    disable_images: bool = False,
) -> None:
    """Execute the universal curriculum conversion pipeline."""
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        console.print(f"[bold red]❌ Input PDF not found:[/bold red] {pdf_file}")
        console.print("[yellow]Usage: uv run convert_curriculum.py <path_to_pdf> [--output-dir <path>][/yellow]")
        sys.exit(1)

    pdf_stem = pdf_file.stem
    if output_dir:
        out_path = Path(output_dir).resolve()
    else:
        out_path = pdf_file.parent / f"output_{sanitize_filename(pdf_stem)}"

    cache_dir = out_path / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_md_path = cache_dir / "raw_marker.md"

    # Optional catalog overrides
    catalog_overrides = None
    if catalog_file:
        c_path = Path(catalog_file)
        if c_path.exists():
            try:
                if c_path.suffix in (".yaml", ".yml"):
                    catalog_overrides = yaml.safe_load(c_path.read_text(encoding="utf-8"))
                else:
                    catalog_overrides = json.loads(c_path.read_text(encoding="utf-8"))
                console.print(f"[bold green]✔ Loaded metadata overrides from:[/bold green] {c_path}")
            except Exception as e:
                console.print(f"[yellow]⚠️ Failed to load catalog file {c_path}: {e}[/yellow]")

    resolved_device = detect_device(device)
    console.print(f"[bold cyan]Universal Curriculum Converter[/bold cyan]")
    console.print(f"📄 Input PDF: [yellow]{pdf_file}[/yellow]")
    console.print(f"📁 Output Directory: [yellow]{out_path}[/yellow]")
    console.print(f"⚙️ Target Device: [green]{resolved_device}[/green] (requested: {device})")
    console.print(f"🚀 Marker Mode: [green]{mode}[/green]")
    console.print(f"🏷️ Target Unit Prefixes: [magenta]{', '.join(unit_prefixes)}[/magenta]")
    if page_range:
        console.print(f"📑 Page Range: [magenta]{page_range}[/magenta]")

    # Step 1: Run Marker or read cached raw markdown
    if skip_marker and raw_md_path.exists():
        console.print(f"[bold green]✔ Skipping Marker:[/bold green] Reusing cached raw extraction from [cyan]{raw_md_path}[/cyan]")
        raw_text = raw_md_path.read_text(encoding="utf-8")
    else:
        marker_single_bin = shutil.which("marker_single")
        if not marker_single_bin:
            candidate = Path(sys.executable).parent / "marker_single"
            if candidate.exists():
                marker_single_bin = str(candidate)
            else:
                marker_single_bin = "marker_single"

        marker_cmd = [
            marker_single_bin,
            str(pdf_file),
            "--output_dir",
            str(cache_dir),
            "--mode",
            mode,
            "--TableProcessor_disable_ocr",
            "--EquationProcessor_disable_ocr",
        ]
        if page_range:
            marker_cmd.extend(["--page_range", page_range])
        if disable_images:
            marker_cmd.append("--disable_image_extraction")

        console.print(f"[bold blue]⏳ Running Marker conversion...[/bold blue]")
        res = subprocess.run(marker_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            console.print(f"[bold red]❌ Marker execution failed![/bold red]\n{res.stderr}")
            sys.exit(res.returncode)

        candidates = list(cache_dir.rglob("*.md"))
        if not candidates:
            console.print(f"[bold red]❌ No markdown output found in {cache_dir}[/bold red]")
            sys.exit(1)

        source_extracted = candidates[0]
        raw_text = source_extracted.read_text(encoding="utf-8")
        raw_md_path.write_text(raw_text, encoding="utf-8")
        console.print(f"[bold green]✔ Marker raw extraction saved:[/bold green] {raw_md_path}")

        # Copy any extracted images into assets/images
        img_dest = out_path / "assets" / "images"
        img_dest.mkdir(parents=True, exist_ok=True)
        for ext in ("*.jpeg", "*.png", "*.jpg", "*.webp"):
            for img_file in source_extracted.parent.glob(ext):
                shutil.copy2(img_file, img_dest / img_file.name)

    # Step 2: Clean and sanitize
    console.print(f"[bold blue]🧹 Cleaning and normalizing markdown text...[/bold blue]")
    cleaned_text = clean_markdown_text(raw_text)

    # Determine document title from text or filename
    doc_title = extract_document_title(cleaned_text, pdf_stem.replace("_", " "))

    # Save consolidated full cleaned file
    full_dir = out_path / "full"
    full_dir.mkdir(parents=True, exist_ok=True)
    full_cleaned_file = full_dir / f"{pdf_stem}_full.md"
    full_cleaned_file.write_text(cleaned_text, encoding="utf-8")
    console.print(f"[bold green]✔ Consolidated full markdown:[/bold green] {full_cleaned_file}")

    # Step 3: Dynamic Semantic splitting
    console.print(f"[bold blue]✂️ Semantically discovering and splitting curriculum units...[/bold blue]")
    sections = split_curriculum_markdown(
        full_text=cleaned_text,
        unit_prefixes=unit_prefixes,
        catalog_overrides=catalog_overrides,
    )

    # Step 4: Write optimized modular files & manifests
    write_optimized_markdown(sections, out_path, str(pdf_file), doc_title)
    console.print(f"[bold green]✔ Created {len(sections)} modular files with YAML frontmatter.[/bold green]")
    console.print(f"[bold green]✔ Generated 00_AGENT_MANIFEST.md and agent_manifest.json[/bold green]")

    # Print summary table
    table = Table(title=f"Curriculum Corpus: {doc_title}")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Path / Sample", style="white")

    units = [s for s in sections if s.doc_type == "uaa"]
    sits = [s for s in sections if s.doc_type == "situation_apprentissage"]
    others = [s for s in sections if s.doc_type not in ("uaa", "situation_apprentissage")]

    table.add_row("Learning Units", str(len(units)), f"{unit_prefixes[0].lower()}/*.md")
    table.add_row("Learning Situations", str(len(sits)), "situations_apprentissage/*.md")
    table.add_row("Framework & Reference", str(len(others)), "01_cadre_general.md, etc.")
    table.add_row("Manifests & Full Docs", "3", "00_AGENT_MANIFEST.md, agent_manifest.json, full/*.md")

    console.print(table)
    console.print(f"\n[bold green]🎉 Conversion completed successfully into:[/bold green] [cyan]{out_path}[/cyan]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert ANY curriculum PDF into AI-agent-optimized Markdown using Marker and UV"
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        default="CPEONS D2_D3 TT INFORMATIQUE.pdf",
        help="Path to any curriculum PDF file (default: 'CPEONS D2_D3 TT INFORMATIQUE.pdf')",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=None,
        help="Target output directory (default: './output_<pdf_name>')",
    )
    parser.add_argument(
        "--unit-prefixes",
        default="UAA,Unité,Module,Chapitre",
        help="Comma-separated prefixes for learning units (default: 'UAA,Unité,Module,Chapitre')",
    )
    parser.add_argument(
        "--catalog-file",
        "-c",
        default=None,
        help="Optional external JSON or YAML file with metadata overrides",
    )
    parser.add_argument(
        "--page-range",
        default=None,
        help="Optional page range to convert (e.g. '0-5' or '0,10-15')",
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "balanced"],
        default="fast",
        help="Marker mode: 'fast' for lightweight CPU layout/detectors, 'balanced' for full VLM (default: fast)",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda"],
        default="auto",
        help="Target compute device: 'auto' (detects CUDA or CPU), 'cpu', or 'cuda' (default: auto)",
    )
    parser.add_argument(
        "--skip-marker",
        action="store_true",
        help="Skip Marker OCR extraction and reuse cached raw markdown to rapidly iterate post-processing/splitting",
    )
    parser.add_argument(
        "--disable-images",
        action="store_true",
        help="Disable extracting images from PDF",
    )

    args = parser.parse_args()
    prefixes = tuple(p.strip() for p in args.unit_prefixes.split(",") if p.strip())

    run_conversion_pipeline(
        pdf_path=args.pdf,
        output_dir=args.output_dir,
        page_range=args.page_range,
        mode=args.mode,
        device=args.device,
        unit_prefixes=prefixes,
        catalog_file=args.catalog_file,
        skip_marker=args.skip_marker,
        disable_images=args.disable_images,
    )


if __name__ == "__main__":
    main()
