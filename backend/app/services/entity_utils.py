from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any


ORG_SUFFIXES = ("公司", "集團", "銀行", "醫院", "大學", "學院", "政府", "部", "局", "署", "院", "委員會", "協會", "基金會", "平台", "中心", "研究院")
LOCATION_SUFFIXES = ("市", "縣", "區", "鎮", "鄉", "國", "州", "省", "港", "台灣", "臺灣", "日本", "美國", "中國", "韓國", "歐洲")
PERSON_HINTS = ("表示", "指出", "說", "強調", "認為", "宣布")
GENERIC_TERMS = {"新聞", "資料", "分析", "系統", "平台", "報導", "內容", "相關", "目前", "未來", "今日", "昨日"}


def parse_entities(value: Any) -> list[tuple[str, str]]:
    """保留既有 JSON 格式，避免 service 各自解析。"""
    if not value:
        return []
    raw = value
    if isinstance(value, str):
        try:
            raw = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    output: list[tuple[str, str]] = []
    if not isinstance(raw, list):
        return output
    for item in raw:
        if isinstance(item, (list, tuple)) and item:
            entity = str(item[0]).strip()
            entity_type = str(item[1]).strip() if len(item) > 1 and item[1] else "entity"
        elif isinstance(item, dict):
            entity = str(item.get("entity") or item.get("text") or item.get("name") or "").strip()
            entity_type = str(item.get("type") or item.get("label") or "entity").strip()
        elif isinstance(item, str):
            entity = item.strip()
            entity_type = "entity"
        else:
            continue
        if _valid_entity(entity):
            output.append((entity, entity_type))
    return _dedupe(output)


def fallback_entities_from_row(row: dict[str, Any], limit: int = 12) -> list[tuple[str, str]]:
    existing = parse_entities(row.get("entities"))
    if existing:
        return existing[:limit]

    text = " ".join(str(row.get(key) or "") for key in ("title", "content_clean", "content", "summary"))
    candidates: list[tuple[str, str]] = []
    candidates.extend(_suffix_entities(text, ORG_SUFFIXES, "ORG"))
    candidates.extend(_suffix_entities(text, LOCATION_SUFFIXES, "LOCATION"))
    candidates.extend(_person_candidates(text))

    for term in _keyword_terms(row):
        if _valid_entity(term):
            candidates.append((term, _keyword_type(term)))

    return _dedupe(candidates)[:limit]


def entity_values(row: dict[str, Any], limit: int = 12) -> list[str]:
    return [f"{entity} / {entity_type}" for entity, entity_type in fallback_entities_from_row(row, limit)]


def entity_count_rows(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        counts.update(fallback_entities_from_row(row, 12))
    return [{"entity": entity, "type": typ, "count": count} for (entity, typ), count in counts.most_common(limit)]


def entity_profile_rows(rows: list[dict[str, Any]], group_key: str, label: str, limit: int = 20) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        group = str(row.get(group_key) or "unknown")
        for entity, entity_type in fallback_entities_from_row(row, 12):
            counts[(group, entity, entity_type)] += 1
    return [{label: group, "entity": entity, "type": entity_type, "count": count} for (group, entity, entity_type), count in counts.most_common(limit)]


def fallback_entity_note(rows: list[dict[str, Any]]) -> str | None:
    has_existing = any(parse_entities(row.get("entities")) for row in rows)
    has_fallback = any(fallback_entities_from_row(row) for row in rows)
    if has_fallback and not has_existing:
        return "Entity results use a lightweight rule-based fallback because stored NER outputs are empty."
    return None


def _suffix_entities(text: str, suffixes: tuple[str, ...], entity_type: str) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for suffix in suffixes:
        pattern = rf"[\u4e00-\u9fffA-Za-z0-9]{{2,12}}{re.escape(suffix)}"
        for match in re.findall(pattern, text):
            if _valid_entity(match):
                output.append((match, entity_type))
    return output


def _person_candidates(text: str) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    for hint in PERSON_HINTS:
        for match in re.findall(rf"([\u4e00-\u9fff]{{2,4}}){re.escape(hint)}", text):
            if _valid_entity(match):
                output.append((match, "PERSON_CANDIDATE"))
    return output


def _keyword_terms(row: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    keywords = _json(row.get("keywords"), [])
    for item in keywords:
        if isinstance(item, (list, tuple)) and item:
            terms.append(str(item[0]))
        elif isinstance(item, dict):
            terms.append(str(item.get("term") or item.get("keyword") or ""))
        elif isinstance(item, str):
            terms.append(item)
    if terms:
        return terms[:10]
    tokens = _json(row.get("tokens"), [])
    return [str(token) for token in tokens if _valid_entity(str(token))][:10]


def _keyword_type(term: str) -> str:
    if term.endswith(ORG_SUFFIXES):
        return "ORG"
    if term.endswith(LOCATION_SUFFIXES) or term in LOCATION_SUFFIXES:
        return "LOCATION"
    return "KEYWORD_ENTITY"


def _valid_entity(value: str) -> bool:
    value = value.strip()
    if len(value) < 2 or value in GENERIC_TERMS:
        return False
    if value.isdigit():
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z]", value))


def _dedupe(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    output: list[tuple[str, str]] = []
    for entity, entity_type in items:
        key = (entity.strip(), entity_type.strip() or "entity")
        if key in seen or not _valid_entity(key[0]):
            continue
        seen.add(key)
        output.append(key)
    return output


def _json(value: Any, fallback: Any) -> Any:
    if not value:
        return fallback
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback
