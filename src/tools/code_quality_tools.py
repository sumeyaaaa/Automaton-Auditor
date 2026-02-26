"""
Code quality and best practices analysis tools.
These provide factual evidence that judges can use for better scoring.
Rubric-agnostic - works for any project.

IMPORTANT: Evidence.found means "the detective successfully ran this analysis",
NOT "the result looks good". Judges interpret quality; detectives report facts.
"""
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.state import Evidence


def analyze_code_complexity(repo_path: Path) -> Dict:
    """Analyze code complexity metrics (cyclomatic complexity, nesting depth)."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    complexity_data = {
        "files_analyzed": 0,
        "high_complexity_files": [],
        "max_complexity": 0,
        "average_complexity": 0.0,
        "total_functions": 0,
    }

    complexities = []

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_complexity = 0

            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With, ast.ExceptHandler)):
                    file_complexity += 1

                if isinstance(node, ast.FunctionDef):
                    complexity_data["total_functions"] += 1
                    func_complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, ast.With, ast.ExceptHandler)):
                            func_complexity += 1
                    complexities.append(func_complexity)

            if file_complexity > 20:
                complexity_data["high_complexity_files"].append({
                    "file": str(py_file.relative_to(repo_path)),
                    "complexity": file_complexity,
                })

            complexity_data["files_analyzed"] += 1

        except (SyntaxError, UnicodeDecodeError):
            continue

    if complexities:
        complexity_data["max_complexity"] = max(complexities)
        complexity_data["average_complexity"] = sum(complexities) / len(complexities)

    complexity_data["has_high_complexity"] = len(complexity_data["high_complexity_files"]) > 0

    return complexity_data


def check_docstring_coverage(repo_path: Path) -> Dict:
    """Check docstring coverage for functions and classes."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    stats = {
        "total_functions": 0,
        "functions_with_docstrings": 0,
        "total_classes": 0,
        "classes_with_docstrings": 0,
        "files_analyzed": 0,
        "low_coverage_files": [],
    }

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_functions = 0
            file_functions_with_docs = 0
            file_classes = 0
            file_classes_with_docs = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    stats["total_functions"] += 1
                    file_functions += 1
                    if ast.get_docstring(node):
                        stats["functions_with_docstrings"] += 1
                        file_functions_with_docs += 1

                if isinstance(node, ast.ClassDef):
                    stats["total_classes"] += 1
                    file_classes += 1
                    if ast.get_docstring(node):
                        stats["classes_with_docstrings"] += 1
                        file_classes_with_docs += 1

            if file_functions > 0:
                coverage = file_functions_with_docs / file_functions
                if coverage < 0.5:
                    stats["low_coverage_files"].append({
                        "file": str(py_file.relative_to(repo_path)),
                        "function_coverage": coverage,
                        "functions": file_functions,
                        "with_docs": file_functions_with_docs,
                    })

            stats["files_analyzed"] += 1

        except (SyntaxError, UnicodeDecodeError):
            continue

    if stats["total_functions"] > 0:
        stats["function_coverage"] = stats["functions_with_docstrings"] / stats["total_functions"]
    else:
        stats["function_coverage"] = 0.0

    if stats["total_classes"] > 0:
        stats["class_coverage"] = stats["classes_with_docstrings"] / stats["total_classes"]
    else:
        stats["class_coverage"] = 0.0

    return stats


def check_type_hint_coverage(repo_path: Path) -> Dict:
    """Check type hint coverage in function signatures."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    stats = {
        "total_functions": 0,
        "functions_with_type_hints": 0,
        "files_analyzed": 0,
        "low_coverage_files": [],
    }

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_functions = 0
            file_functions_with_hints = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    stats["total_functions"] += 1
                    file_functions += 1

                    has_return_hint = node.returns is not None
                    has_param_hints = any(arg.annotation is not None for arg in node.args.args)

                    if has_return_hint or has_param_hints:
                        stats["functions_with_type_hints"] += 1
                        file_functions_with_hints += 1

            if file_functions > 0:
                coverage = file_functions_with_hints / file_functions
                if coverage < 0.3:
                    stats["low_coverage_files"].append({
                        "file": str(py_file.relative_to(repo_path)),
                        "type_hint_coverage": coverage,
                        "functions": file_functions,
                        "with_hints": file_functions_with_hints,
                    })

            stats["files_analyzed"] += 1

        except (SyntaxError, UnicodeDecodeError):
            continue

    if stats["total_functions"] > 0:
        stats["type_hint_coverage"] = stats["functions_with_type_hints"] / stats["total_functions"]
    else:
        stats["type_hint_coverage"] = 0.0

    return stats


def check_error_handling_quality(repo_path: Path) -> Dict:
    """Check error handling patterns (try/except coverage, specific exceptions)."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    stats = {
        "total_functions": 0,
        "functions_with_error_handling": 0,
        "bare_excepts": 0,
        "specific_exceptions": 0,
        "files_analyzed": 0,
        "poor_error_handling_files": [],
    }

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_functions = 0
            file_functions_with_handling = 0
            file_bare_excepts = 0
            file_specific_excepts = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    file_functions += 1
                    stats["total_functions"] += 1

                    for child in ast.walk(node):
                        if isinstance(child, ast.Try):
                            stats["functions_with_error_handling"] += 1
                            file_functions_with_handling += 1

                            for handler in child.handlers:
                                if handler.type is None:
                                    file_bare_excepts += 1
                                    stats["bare_excepts"] += 1
                                else:
                                    file_specific_excepts += 1
                                    stats["specific_exceptions"] += 1

            if file_functions > 0:
                handling_coverage = file_functions_with_handling / file_functions
                if handling_coverage < 0.3 or file_bare_excepts > 0:
                    stats["poor_error_handling_files"].append({
                        "file": str(py_file.relative_to(repo_path)),
                        "handling_coverage": handling_coverage,
                        "bare_excepts": file_bare_excepts,
                        "functions": file_functions,
                    })

            stats["files_analyzed"] += 1

        except (SyntaxError, UnicodeDecodeError):
            continue

    if stats["total_functions"] > 0:
        stats["error_handling_coverage"] = stats["functions_with_error_handling"] / stats["total_functions"]
    else:
        stats["error_handling_coverage"] = 0.0

    return stats


def check_test_coverage_indicators(repo_path: Path) -> Dict:
    """Check for test files and test coverage indicators."""
    test_dirs = [
        repo_path / "tests",
        repo_path / "test",
        repo_path / "__tests__",
        repo_path / "tests" / "unit",
        repo_path / "tests" / "integration",
    ]

    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(list(test_dir.rglob("test_*.py")))
            test_files.extend(list(test_dir.rglob("*_test.py")))

    coverage_configs = [
        repo_path / ".coveragerc",
        repo_path / "pyproject.toml",
        repo_path / "setup.cfg",
    ]

    has_coverage_config = any(p.exists() for p in coverage_configs)

    has_pytest = False
    has_unittest = False

    for test_file in test_files[:10]:
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "import pytest" in content or "from pytest" in content:
                    has_pytest = True
                if "import unittest" in content or "from unittest" in content:
                    has_unittest = True
        except Exception:
            continue

    return {
        "has_test_directory": len(test_files) > 0,
        "test_file_count": len(test_files),
        "has_coverage_config": has_coverage_config,
        "uses_pytest": has_pytest,
        "uses_unittest": has_unittest,
        "test_files": [str(f.relative_to(repo_path)) for f in test_files[:10]],
    }


def check_dependency_management(repo_path: Path) -> Dict:
    """Check dependency management files and practices."""
    dependency_files = {
        "requirements.txt": (repo_path / "requirements.txt").exists(),
        "requirements-dev.txt": (repo_path / "requirements-dev.txt").exists(),
        "pyproject.toml": (repo_path / "pyproject.toml").exists(),
        "setup.py": (repo_path / "setup.py").exists(),
        "Pipfile": (repo_path / "Pipfile").exists(),
        "poetry.lock": (repo_path / "poetry.lock").exists(),
        "package.json": (repo_path / "package.json").exists(),
    }

    has_dependency_file = any(dependency_files.values())

    pinned_dependencies = False
    if (repo_path / "requirements.txt").exists():
        try:
            with open(repo_path / "requirements.txt", "r") as f:
                content = f.read()
                lines = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]
                if lines:
                    pinned_count = sum(1 for line in lines if "==" in line or "~=" in line or ">=" in line)
                    pinned_dependencies = pinned_count / len(lines) > 0.5
        except Exception:
            pass

    return {
        "has_dependency_file": has_dependency_file,
        "dependency_files": {k: v for k, v in dependency_files.items() if v},
        "pinned_dependencies": pinned_dependencies,
    }


def check_code_duplication_indicators(repo_path: Path) -> Dict:
    """Check for potential code duplication patterns."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    function_signatures = {}
    duplicate_indicators = []

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    sig = f"{node.name}({len(node.args.args)} params)"

                    if sig not in function_signatures:
                        function_signatures[sig] = []
                    function_signatures[sig].append(str(py_file.relative_to(repo_path)))

        except (SyntaxError, UnicodeDecodeError):
            continue

    for sig, files in function_signatures.items():
        if len(files) > 1:
            duplicate_indicators.append({
                "signature": sig,
                "files": files,
                "count": len(files),
            })

    return {
        "potential_duplicates": len(duplicate_indicators),
        "duplicate_indicators": duplicate_indicators[:10],
    }


def check_import_organization(repo_path: Path) -> Dict:
    """Check import organization and best practices."""
    src_dir = repo_path / "src"
    if not src_dir.exists():
        src_dir = repo_path

    stats = {
        "files_analyzed": 0,
        "files_with_organized_imports": 0,
        "files_with_wildcard_imports": 0,
        "files_with_unused_imports_indicators": 0,
    }

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            imports = [line for line in lines if line.strip().startswith(("import ", "from "))]

            if not imports:
                continue

            stats["files_analyzed"] += 1

            if any("import *" in imp for imp in imports):
                stats["files_with_wildcard_imports"] += 1

            stdlib_keywords = ["import os", "import sys", "import json", "import re", "import pathlib"]
            third_party_keywords = ["from langchain", "from pydantic", "import git"]

            has_stdlib = any(kw in imp for imp in imports for kw in stdlib_keywords)
            has_third_party = any(kw in imp for imp in imports for kw in third_party_keywords)

            if has_stdlib and has_third_party:
                stdlib_idx = min(
                    (i for i, imp in enumerate(imports) if any(kw in imp for kw in stdlib_keywords)),
                    default=len(imports),
                )
                third_party_idx = min(
                    (i for i, imp in enumerate(imports) if any(kw in imp for kw in third_party_keywords)),
                    default=len(imports),
                )

                if stdlib_idx < third_party_idx:
                    stats["files_with_organized_imports"] += 1

        except (SyntaxError, UnicodeDecodeError):
            continue

    if stats["files_analyzed"] > 0:
        stats["import_organization_score"] = stats["files_with_organized_imports"] / stats["files_analyzed"]
    else:
        stats["import_organization_score"] = 0.0

    return stats


# ══════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════

def check_general_code_quality(
    repo_path: Path,
    rubric_dimensions: List[Dict],
) -> List[Evidence]:
    """Run general code quality checks that help judges provide better feedback.

    IMPORTANT: Evidence.found = "analysis ran successfully", NOT "code is good".
    Judges interpret quality from the content/rationale fields.
    Detectives just report facts.
    """
    evidence_list = []

    # ── Code complexity ──
    try:
        result = analyze_code_complexity(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Analyze code complexity metrics",
            found=result.get("files_analyzed", 0) > 0,  # analysis ran
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Average complexity: {result.get('average_complexity', 0.0):.2f}. "
                f"{len(result.get('high_complexity_files', []))} files with high complexity."
            ),
            confidence=0.8 if not result.get("has_high_complexity") else 0.5,
        ))
    except Exception:
        pass

    # ── Docstring coverage ──
    try:
        result = check_docstring_coverage(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check docstring coverage",
            found=result.get("files_analyzed", 0) > 0,  # analysis ran
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Function docstring coverage: {result.get('function_coverage', 0.0):.1%}. "
                f"{result.get('functions_with_docstrings', 0)}/{result.get('total_functions', 0)} functions documented."
            ),
            confidence=0.7 if result.get("function_coverage", 0.0) > 0.5 else 0.4,
        ))
    except Exception:
        pass

    # ── Type hint coverage ──
    try:
        result = check_type_hint_coverage(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check type hint coverage",
            found=result.get("files_analyzed", 0) > 0,  # analysis ran
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Type hint coverage: {result.get('type_hint_coverage', 0.0):.1%}. "
                f"{result.get('functions_with_type_hints', 0)}/{result.get('total_functions', 0)} functions have type hints."
            ),
            confidence=0.7 if result.get("type_hint_coverage", 0.0) > 0.3 else 0.4,
        ))
    except Exception:
        pass

    # ── Error handling quality ──
    try:
        result = check_error_handling_quality(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check error handling quality",
            found=result.get("files_analyzed", 0) > 0,  # analysis ran
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Error handling coverage: {result.get('error_handling_coverage', 0.0):.1%}. "
                f"Bare excepts: {result.get('bare_excepts', 0)}. "
                f"Specific exceptions: {result.get('specific_exceptions', 0)}"
            ),
            confidence=0.8 if result.get("bare_excepts", 0) == 0 else 0.4,
        ))
    except Exception:
        pass

    # ── Test coverage indicators ──
    try:
        result = check_test_coverage_indicators(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check test coverage indicators",
            found=True,  # analysis always runs (checks file existence)
            location=str(repo_path),
            content=json.dumps(result),
            rationale=(
                f"Test files: {result.get('test_file_count', 0)}. "
                f"Coverage config: {result.get('has_coverage_config', False)}. "
                f"Uses pytest: {result.get('uses_pytest', False)}"
            ),
            confidence=0.8 if result.get("has_test_directory") else 0.3,
        ))
    except Exception:
        pass

    # ── Dependency management ──
    try:
        result = check_dependency_management(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check dependency management",
            found=True,  # analysis always runs (checks file existence)
            location=str(repo_path),
            content=json.dumps(result),
            rationale=(
                f"Dependency files: {len(result.get('dependency_files', {}))}. "
                f"Pinned dependencies: {result.get('pinned_dependencies', False)}"
            ),
            confidence=0.7 if result.get("has_dependency_file") else 0.2,
        ))
    except Exception:
        pass

    # ── Code duplication indicators ──
    try:
        result = check_code_duplication_indicators(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check for code duplication indicators",
            found=True,  # analysis always runs
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Potential duplicates: {result.get('potential_duplicates', 0)}. "
                "Functions with same signature found in multiple files."
            ),
            confidence=0.7 if result.get("potential_duplicates", 0) == 0 else 0.5,
        ))
    except Exception:
        pass

    # ── Import organization ──
    try:
        result = check_import_organization(repo_path)
        evidence_list.append(Evidence(
            criterion_id="code_quality",
            goal="Check import organization",
            found=result.get("files_analyzed", 0) > 0,  # analysis ran
            location=str(repo_path / "src"),
            content=json.dumps(result),
            rationale=(
                f"Import organization score: {result.get('import_organization_score', 0.0):.2f}. "
                f"Wildcard imports: {result.get('files_with_wildcard_imports', 0)} files"
            ),
            confidence=0.6 if result.get("import_organization_score", 0.0) > 0.5 else 0.4,
        ))
    except Exception:
        pass

    return evidence_list