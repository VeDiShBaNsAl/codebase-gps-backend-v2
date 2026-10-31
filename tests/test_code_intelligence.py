from code_intelligence import analyze_repository, dependencies, direct_callers


def test_analyzer_builds_a_resolved_python_call_graph(tmp_path):
    (tmp_path / "service.py").write_text(
        "def helper():\n    return 1\n\n"
        "def run():\n    return helper()\n",
        encoding="utf-8",
    )

    graph = analyze_repository(str(tmp_path))
    functions = {node.name: node for node in graph["nodes"] if node.type == "FUNCTION"}
    calls = [edge for edge in graph["edges"] if edge.type == "CALLS"]

    assert graph["total_files"] == 1
    assert {"helper", "run"} <= functions.keys()
    assert any(edge.source == functions["run"].id and edge.target == functions["helper"].id and edge.resolution == "resolved" for edge in calls)
    assert direct_callers(graph, functions["helper"].id) == [functions["run"].id]
    assert dependencies(graph, functions["run"].id) == [functions["helper"].id]


def test_analyzer_keeps_unresolved_calls_explicit(tmp_path):
    (tmp_path / "service.py").write_text("def run():\n    return remote_client.execute()\n", encoding="utf-8")

    graph = analyze_repository(str(tmp_path))
    calls = [edge for edge in graph["edges"] if edge.type == "CALLS"]

    assert len(calls) == 1
    assert calls[0].resolution == "unresolved"
    assert calls[0].target.startswith("unresolved:")


def test_analyzer_discovers_typescript_functions_and_imports(tmp_path):
    (tmp_path / "util.ts").write_text("export function helper() { return 1; }\n", encoding="utf-8")
    (tmp_path / "main.ts").write_text('import { helper } from "./util";\nexport const run = () => helper();\n', encoding="utf-8")

    graph = analyze_repository(str(tmp_path))

    assert graph["languages"] == ["typescript"]
    assert any(node.name == "run" for node in graph["nodes"])
    assert any(edge.type == "IMPORTS" and edge.resolution == "resolved" for edge in graph["edges"])
