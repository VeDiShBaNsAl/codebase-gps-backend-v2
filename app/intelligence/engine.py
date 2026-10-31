"""Preserved deterministic Person 4 analysis logic, isolated from API/SQLite concerns."""
from __future__ import annotations

import re
from collections import Counter, defaultdict, deque
from math import log

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "with", "when", "where", "will", "would", "should", "can", "could", "not", "after", "before", "into"}
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|[_-]+")


def tokenize(text: str) -> list[str]:
    return [part.lower() for raw in WORD.findall(text) for part in BOUNDARY.split(raw) if len(part) > 1 and part.lower() not in STOP]


def keywords(title: str, description: str) -> list[str]:
    counts = Counter(tokenize(description)); counts.update({word: 3 for word in tokenize(title)})
    return [word for word, _ in sorted(counts.items(), key=lambda value: (-value[1], value[0]))[:15]]


def rank(components: list[dict], terms: list[str], limit: int) -> list[dict]:
    components = [component for component in components if not component["is_test"]]
    docs: dict[str, tuple[Counter, dict[str, set[str]]]] = {}
    for component in components:
        fields = {"name": tokenize(component["name"]), "path": tokenize(component["location"]["path"]), "content": tokenize(component.get("content", ""))}
        frequencies, origins = Counter(), defaultdict(set)
        for field, weight in (("name", 4), ("path", 2), ("content", 1)):
            for word in fields[field]: frequencies[word] += weight; origins[word].add(field)
        docs[component["id"]] = frequencies, origins
    if not docs: return []
    average = sum(sum(freq.values()) for freq, _ in docs.values()) / len(docs)
    frequency = {term: sum(term in freq for freq, _ in docs.values()) for term in terms}
    results = []
    for component in components:
        frequencies, origins = docs[component["id"]]; matched = sorted(term for term in terms if term in frequencies)
        if not matched: continue
        length, score = sum(frequencies.values()), 0.0
        for term in matched:
            tf = frequencies[term]; idf = log(1 + (len(docs) - frequency[term] + .5) / (frequency[term] + .5))
            score += idf * (tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average)))
        detail = ", ".join(f"{term} ({'/'.join(sorted(origins[term]))})" for term in matched)
        results.append({"component": component, "score": round(score, 6), "matched_keywords": matched, "evidence": [{"kind": "keyword_match", "detail": f"Matched issue keywords and fields: {detail}", "location": component["location"]}]})
    return sorted(results, key=lambda item: (-item["score"], item["component"]["id"]))[:limit]


def _walk(seeds: set[str], components: dict[str, dict], edges: list[dict], depth: int, outgoing: bool) -> list[dict]:
    graph = defaultdict(list)
    for edge in edges:
        if edge["source_id"] not in components or edge["target_id"] not in components: continue
        start, end = (edge["source_id"], edge["target_id"]) if outgoing else (edge["target_id"], edge["source_id"])
        graph[start].append((end, edge))
    queue, seen, result = deque((node, 0) for node in sorted(seeds)), set(seeds), []
    while queue:
        node, distance = queue.popleft()
        if distance >= depth: continue
        for target, edge in sorted(graph[node], key=lambda item: item[0]):
            if target in seen: continue
            seen.add(target); next_distance = distance + 1
            result.append({"component": components[target], "relationship": "depends_on" if outgoing else "depended_on_by", "distance": next_distance, "evidence": {"kind": "dependency_edge", "detail": edge["evidence"], "location": edge["location"]}})
            queue.append((target, next_distance))
    return result


def _tests(relevant: set[str], components: dict[str, dict], test_edges: list[dict]) -> list[dict]:
    result = []
    for edge in test_edges:
        source, target = edge["source_id"], edge["target_id"]
        test_id = source if source in components and components[source]["is_test"] else target
        other_id = target if test_id == source else source
        if test_id in components and other_id in relevant:
            result.append({"component": components[test_id], "relationship": "test_connected_to", "distance": 1, "evidence": {"kind": "test_edge", "detail": edge["evidence"], "location": edge["location"]}})
    return sorted({item["component"]["id"]: item for item in result}.values(), key=lambda item: item["component"]["id"])


def investigate(issue: dict, snapshot: dict, max_results: int = 10, depth: int = 2) -> dict:
    terms = keywords(issue["title"], issue.get("description", "")); by_id = {item["id"]: item for item in snapshot["components"]}
    ranked = rank(snapshot["components"], terms, max_results); seeds = {item["component"]["id"] for item in ranked}
    related = _walk(seeds, by_id, snapshot["dependency_edges"], depth, True) + _walk(seeds, by_id, snapshot["dependency_edges"], depth, False)
    related = [item for item in related if not item["component"]["is_test"]]
    return {"keywords": terms, "ranked_components": ranked, "related_components": related, "related_tests": _tests(seeds | {item["component"]["id"] for item in related}, by_id, snapshot["test_edges"]), "diagnostics": snapshot["diagnostics"]}


def impact(selected_id: str, snapshot: dict, depth: int = 5) -> dict | None:
    by_id = {item["id"]: item for item in snapshot["components"]}
    if selected_id not in by_id: return None
    dependencies = _walk({selected_id}, by_id, snapshot["dependency_edges"], depth, True)
    dependents = _walk({selected_id}, by_id, snapshot["dependency_edges"], depth, False)
    relevant = {selected_id} | {item["component"]["id"] for item in dependencies + dependents}
    return {"selected_component": by_id[selected_id], "dependencies": dependencies, "dependents": dependents, "related_tests": _tests(relevant, by_id, snapshot["test_edges"]), "diagnostics": snapshot["diagnostics"]}
