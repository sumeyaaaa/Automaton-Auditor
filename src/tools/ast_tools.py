"""
AST-based code analysis tools.
Uses Python's ast module (not regex) for structural code verification.
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional

from src.tools.file_finder import find_file_recursive, find_file_fuzzy


def check_stategraph(repo_path: Path) -> Dict:
    """Check for LangGraph StateGraph instantiation using AST.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with StateGraph analysis results
    """
    graph_file = find_file_recursive(repo_path, "graph.py")

    if not graph_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "graph")
        if fuzzy_matches:
            graph_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "error": "graph.py not found (searched recursively)",
                "searched_locations": ["src/graph.py", "graph.py", "lib/graph.py"],
            }

    try:
        with open(graph_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = StateGraphAnalyzer()
        analyzer.visit(tree)

        return analyzer.get_results()
    except SyntaxError as e:
        return {
            "found": True,
            "error": f"Syntax error in graph.py: {str(e)}",
        }
    except Exception as e:
        return {
            "found": True,
            "error": f"Error analyzing graph: {str(e)}",
        }


def check_pydantic_models(repo_path: Path) -> Dict:
    """Check for Pydantic models using AST.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with Pydantic model analysis
    """
    state_file = find_file_recursive(repo_path, "state.py")

    if not state_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "state")
        if fuzzy_matches:
            state_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "has_pydantic": False,
                "has_reducers": False,
                "error": "state.py not found (searched recursively)",
            }

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = PydanticAnalyzer()
        analyzer.visit(tree)

        return analyzer.get_results()
    except Exception as e:
        return {
            "found": True,
            "error": str(e),
        }


def check_parallel_edges(repo_path: Path) -> Dict:
    """Check for parallel fan-out/fan-in patterns using AST.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with parallel edge analysis
    """
    graph_file = find_file_recursive(repo_path, "graph.py")

    if not graph_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "graph")
        if fuzzy_matches:
            graph_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "has_parallel_edges": False,
                "error": "graph.py not found (searched recursively)",
            }

    try:
        with open(graph_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = ParallelEdgeAnalyzer()
        analyzer.visit(tree)

        return analyzer.get_results()
    except Exception as e:
        return {
            "found": True,
            "error": str(e),
        }


def check_sandboxing(repo_path: Path) -> Dict:
    """Check for proper sandboxing in tool implementations.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with sandboxing analysis
    """
    tools_dir = repo_path / "src" / "tools"
    if not tools_dir.exists():
        return {
            "found": False,
            "has_sandboxing": False,
            "has_os_system": False,
        }

    has_sandboxing = False
    has_os_system = False
    uses_subprocess = False

    for tool_file in tools_dir.glob("*.py"):
        try:
            with open(tool_file, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)
                tempfile_checker = SandboxingAnalyzer()
                tempfile_checker.visit(tree)
                if tempfile_checker.has_tempfile:
                    has_sandboxing = True
            except Exception:
                pass

            if "os.system" in content:
                has_os_system = True
            if "subprocess.run" in content or "subprocess.Popen" in content:
                uses_subprocess = True
        except Exception:
            continue

    return {
        "found": True,
        "has_sandboxing": has_sandboxing,
        "has_os_system": has_os_system,
        "uses_subprocess": uses_subprocess,
        "security_score": "safe" if has_sandboxing and not has_os_system else "unsafe",
    }


def check_structured_output(repo_path: Path) -> Dict:
    """Check for structured output enforcement in judge nodes.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with structured output analysis
    """
    judges_file = find_file_recursive(repo_path, "judges.py")

    if not judges_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "judge")
        if fuzzy_matches:
            judges_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "has_structured_output": False,
                "error": "judges.py not found (searched recursively)",
            }

    try:
        with open(judges_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = StructuredOutputAnalyzer()
        analyzer.visit(tree)

        has_with_structured = ".with_structured_output" in source_code
        has_bind_tools = ".bind_tools" in source_code
        has_pydantic_validation = "JudicialOpinion" in source_code

        return {
            "found": True,
            "has_structured_output": analyzer.has_structured_output or has_with_structured or has_bind_tools,
            "has_pydantic_validation": has_pydantic_validation,
            "methods_used": {
                "with_structured_output": has_with_structured or analyzer.has_structured_output,
                "bind_tools": has_bind_tools,
            },
        }
    except Exception as e:
        return {
            "found": True,
            "error": str(e),
        }


def check_security(repo_path: Path) -> Dict:
    """Comprehensive security check for forbidden patterns.

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with security analysis
    """
    src_dir = repo_path / "src"
    if not src_dir.exists():
        return {
            "found": False,
            "security_issues": [],
        }

    security_issues = []

    for py_file in src_dir.rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "os.system" in content:
                security_issues.append({
                    "file": str(py_file.relative_to(repo_path)),
                    "issue": "os.system() detected - security violation",
                    "severity": "high",
                })

            if "eval(" in content or "exec(" in content:
                security_issues.append({
                    "file": str(py_file.relative_to(repo_path)),
                    "issue": "eval() or exec() detected - security violation",
                    "severity": "high",
                })
        except Exception:
            continue

    return {
        "found": True,
        "security_issues": security_issues,
        "is_secure": len(security_issues) == 0,
    }


# ──────────────────────────────────────────────
# NEW: Judicial nuance check
# ──────────────────────────────────────────────

def check_judge_prompt_diversity(repo_path: Path) -> Dict:
    """Check that judge nodes use distinct personas/prompts (not copy-paste).

    Looks for:
    - Multiple judge functions or a factory with distinct persona parameters
    - Distinct system prompts per judge (Prosecutor, Defense, TechLead)
    - Persona-specific keywords in prompts (e.g. "security", "merit", "pragmatic")

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with judicial nuance analysis
    """
    judges_file = find_file_recursive(repo_path, "judges.py")

    if not judges_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "judge")
        if fuzzy_matches:
            judges_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "has_diverse_prompts": False,
                "error": "judges.py not found (searched recursively)",
            }

    try:
        with open(judges_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = JudgePromptAnalyzer()
        analyzer.visit(tree)

        results = analyzer.get_results()

        # Also do string-level checks for persona keywords
        source_lower = source_code.lower()

        persona_keywords = {
            "prosecutor": [
                "prosecutor", "prosecution", "flaw", "violation",
                "security", "weakness", "gap", "missing",
            ],
            "defense": [
                "defense", "defence", "merit", "strength",
                "mitigating", "credit", "positive", "achievement",
            ],
            "tech_lead": [
                "tech lead", "techlead", "pragmatic", "engineering",
                "architecture", "implementation", "practical", "maintainab",
            ],
        }

        personas_found = {}
        for persona, keywords in persona_keywords.items():
            hits = [kw for kw in keywords if kw in source_lower]
            personas_found[persona] = {
                "keyword_hits": len(hits),
                "keywords_matched": hits,
            }

        distinct_personas = sum(
            1 for p in personas_found.values() if p["keyword_hits"] >= 2
        )

        results["persona_analysis"] = personas_found
        results["distinct_personas_detected"] = distinct_personas
        results["has_diverse_prompts"] = (
            results.get("has_diverse_prompts", False) or distinct_personas >= 2
        )

        return results

    except Exception as e:
        return {
            "found": True,
            "has_diverse_prompts": False,
            "error": str(e),
        }


# ──────────────────────────────────────────────
# NEW: Chief Justice synthesis rules check
# ──────────────────────────────────────────────

def check_synthesis_rules(repo_path: Path) -> Dict:
    """Check for deterministic synthesis rules in Chief Justice node.

    Looks for:
    - A dedicated justice/synthesis file
    - Conditional score resolution logic (if/elif chains, match/case)
    - Specific rule patterns: security override, variance handling, weighted avg
    - Absence of LLM calls (synthesis should be deterministic, not LLM-based)

    Args:
        repo_path: Path to the cloned repository

    Returns:
        Dictionary with synthesis rules analysis
    """
    # Search for justice.py, chief_justice.py, synthesis.py
    justice_file = None
    for filename in ["justice.py", "chief_justice.py", "synthesis.py"]:
        justice_file = find_file_recursive(repo_path, filename)
        if justice_file:
            break

    if not justice_file:
        fuzzy_matches = find_file_fuzzy(repo_path, "justice")
        if not fuzzy_matches:
            fuzzy_matches = find_file_fuzzy(repo_path, "synthesis")
        if fuzzy_matches:
            justice_file = fuzzy_matches[0]
        else:
            return {
                "found": False,
                "has_synthesis_rules": False,
                "is_deterministic": False,
                "error": "justice.py / synthesis.py not found (searched recursively)",
            }

    try:
        with open(justice_file, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        analyzer = SynthesisRulesAnalyzer()
        analyzer.visit(tree)

        results = analyzer.get_results()

        # String-level checks for known synthesis patterns
        source_lower = source_code.lower()

        rule_keywords = {
            "security_override": [
                "security", "cap", "override", "safe_tool",
            ],
            "variance_handling": [
                "variance", "spread", "disagreement", "dissent",
            ],
            "weighted_average": [
                "weight", "weighted", "0.4", "0.3",
            ],
            "fact_supremacy": [
                "evidence", "fact", "confidence", "supremacy",
            ],
        }

        rules_detected = {}
        for rule_name, keywords in rule_keywords.items():
            hits = [kw for kw in keywords if kw in source_lower]
            rules_detected[rule_name] = {
                "detected": len(hits) >= 1,
                "keywords_matched": hits,
            }

        active_rules = sum(1 for r in rules_detected.values() if r["detected"])

        # Check if file uses LLM (non-deterministic = bad for synthesis)
        uses_llm = any(
            pattern in source_code
            for pattern in ["get_llm(", "ChatOpenAI(", "ChatDeepSeek(", ".invoke("]
        )

        results["rules_detected"] = rules_detected
        results["active_rule_count"] = active_rules
        results["has_synthesis_rules"] = active_rules >= 2
        results["uses_llm"] = uses_llm
        results["is_deterministic"] = not uses_llm and active_rules >= 1

        return results

    except Exception as e:
        return {
            "found": True,
            "has_synthesis_rules": False,
            "is_deterministic": False,
            "error": str(e),
        }


# ══════════════════════════════════════════════
# AST Analyzer Classes
# ══════════════════════════════════════════════


class StateGraphAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze LangGraph StateGraph structure."""

    def __init__(self):
        self.has_stategraph = False
        self.has_parallel_edges = False
        self.has_conditional_edges = False
        self.node_names = []
        self.edge_patterns = []

    def visit_ImportFrom(self, node):
        # Catch all common LangGraph import patterns:
        #   from langgraph.graph import StateGraph
        #   from langgraph.graph.state import StateGraph
        #   from langgraph import StateGraph
        if node.module and ("langgraph" in node.module):
            for alias in node.names:
                if alias.name == "StateGraph" or alias.name == "END" or alias.name == "START":
                    self.has_stategraph = True
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_node":
                # Catches: builder.add_node("name", func)
                # Works for both bare Expr and Assign contexts
                if len(node.args) >= 1:
                    node_name = self._extract_name(node.args[0])
                    if node_name:
                        self.node_names.append(node_name)
            elif node.func.attr == "add_edge":
                self.has_parallel_edges = True
                if len(node.args) >= 2:
                    self.edge_patterns.append({
                        "from": self._extract_name(node.args[0]),
                        "to": self._extract_name(node.args[1]),
                    })
            elif node.func.attr == "add_conditional_edges":
                self.has_conditional_edges = True
        self.generic_visit(node)

    def _extract_name(self, node) -> Optional[str]:
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return str(node.value) if isinstance(node.value, str) else None
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            # Fan-in/fan-out: add_edge(["node1", "node2"], "target")
            names = [self._extract_name(elt) for elt in node.elts]
            names = [n for n in names if n]
            return f"[{', '.join(names)}]" if names else f"[{len(node.elts)} nodes]"
        return None

    def get_results(self) -> Dict:
        return {
            "found": True,
            "has_stategraph": self.has_stategraph,
            "has_parallel_edges": self.has_parallel_edges,
            "has_conditional_edges": self.has_conditional_edges,
            "node_count": len(self.node_names),
            "nodes": self.node_names,
            "edge_count": len(self.edge_patterns),
        }


class PydanticAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Pydantic model usage."""

    def __init__(self):
        self.has_pydantic = False
        self.has_typeddict = False
        self.has_reducers = False
        self.has_evidence = False
        self.has_judicial_opinion = False

    def visit_ImportFrom(self, node):
        if node.module == "pydantic":
            self.has_pydantic = True
        elif node.module == "typing" or node.module == "typing_extensions":
            for alias in node.names:
                if alias.name == "TypedDict":
                    self.has_typeddict = True
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        if "Evidence" in node.name:
            self.has_evidence = True
        if "JudicialOpinion" in node.name or "Opinion" in node.name:
            self.has_judicial_opinion = True

        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                self.has_pydantic = True
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.annotation, ast.Subscript):
            if isinstance(node.annotation.value, ast.Name):
                if node.annotation.value.id == "Annotated":
                    self.has_reducers = True
        self.generic_visit(node)

    def get_results(self) -> Dict:
        return {
            "found": True,
            "has_pydantic": self.has_pydantic,
            "has_typeddict": self.has_typeddict,
            "has_reducers": self.has_reducers,
            "has_evidence": self.has_evidence,
            "has_judicial_opinion": self.has_judicial_opinion,
            "is_properly_typed": self.has_pydantic or self.has_typeddict,
        }


class ParallelEdgeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze parallel edge patterns."""

    def __init__(self):
        self.edge_calls = []
        self.has_fan_out = False
        self.has_fan_in = False

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_edge":
                if len(node.args) >= 2:
                    from_node = self._extract_name(node.args[0])
                    to_node = self._extract_name(node.args[1])
                    self.edge_calls.append((from_node, to_node))
        self.generic_visit(node)

    def _extract_name(self, node) -> Optional[str]:
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return str(node.value) if isinstance(node.value, str) else None
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return f"[{len(node.elts)} nodes]"
        return None

    def get_results(self) -> Dict:
        from_nodes = {}
        for from_node, to_node in self.edge_calls:
            if from_node not in from_nodes:
                from_nodes[from_node] = []
            from_nodes[from_node].append(to_node)

        for from_node, to_nodes in from_nodes.items():
            if len(to_nodes) > 1:
                self.has_fan_out = True

        to_nodes_map = {}
        for from_node, to_node in self.edge_calls:
            if to_node not in to_nodes_map:
                to_nodes_map[to_node] = []
            to_nodes_map[to_node].append(from_node)

        for to_node, from_nodes_list in to_nodes_map.items():
            if len(from_nodes_list) > 1:
                self.has_fan_in = True

        return {
            "found": True,
            "has_parallel_edges": len(self.edge_calls) > 0,
            "has_fan_out": self.has_fan_out,
            "has_fan_in": self.has_fan_in,
            "edge_count": len(self.edge_calls),
        }


class SandboxingAnalyzer(ast.NodeVisitor):
    """AST visitor to check for tempfile usage."""

    def __init__(self):
        self.has_tempfile = False

    def visit_ImportFrom(self, node):
        if node.module == "tempfile":
            self.has_tempfile = True
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id == "TemporaryDirectory":
                self.has_tempfile = True
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == "TemporaryDirectory" or node.func.attr == "mkdtemp":
                self.has_tempfile = True
        self.generic_visit(node)


class StructuredOutputAnalyzer(ast.NodeVisitor):
    """AST visitor to check for structured output usage."""

    def __init__(self):
        self.has_structured_output = False

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "with_structured_output":
                self.has_structured_output = True
            elif node.func.attr == "bind_tools":
                self.has_structured_output = True
        self.generic_visit(node)


# ──────────────────────────────────────────────
# NEW: Judge prompt diversity analyzer
# ──────────────────────────────────────────────

class JudgePromptAnalyzer(ast.NodeVisitor):
    """AST visitor to check for diverse judge prompts/personas.

    Looks for:
    - Multiple distinct judge function definitions
    - A factory pattern with persona parameter
    - Distinct string literals (system prompts) per judge
    """

    def __init__(self):
        self.judge_functions: list[str] = []
        self.has_factory_pattern = False
        self.string_constants: list[str] = []
        self.persona_params: list[str] = []

    def visit_FunctionDef(self, node):
        name_lower = node.name.lower()
        # Detect judge-related function names
        judge_keywords = [
            "prosecutor", "defense", "defence", "tech_lead",
            "techlead", "judge", "judicial",
        ]
        if any(kw in name_lower for kw in judge_keywords):
            self.judge_functions.append(node.name)

        # Check for factory pattern: function with a "persona"/"judge_type"/"role" param
        for arg in node.args.args:
            arg_name = arg.arg.lower()
            if arg_name in ("persona", "judge_type", "role", "judge_name", "judge_role"):
                self.has_factory_pattern = True
                self.persona_params.append(arg.arg)

        self.generic_visit(node)

    def visit_Constant(self, node):
        """Collect string constants (potential prompt templates)."""
        if isinstance(node.value, str) and len(node.value) > 50:
            self.string_constants.append(node.value[:200])
        self.generic_visit(node)

    def visit_Dict(self, node):
        """Check for persona config dicts like JUDGE_PERSONAS = {...}."""
        # If a dict has 3+ keys that look like judge names, it's a persona config
        key_names = []
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                key_names.append(key.value.lower())

        judge_key_hits = sum(
            1 for k in key_names
            if any(j in k for j in ["prosecutor", "defense", "defence", "tech", "lead"])
        )
        if judge_key_hits >= 2:
            self.has_factory_pattern = True

        self.generic_visit(node)

    def get_results(self) -> Dict:
        # Distinct prompts = long string constants that differ from each other
        unique_prompts = len(set(s[:100] for s in self.string_constants))

        has_diverse = (
            self.has_factory_pattern
            or len(self.judge_functions) >= 2
            or unique_prompts >= 2
        )

        return {
            "found": True,
            "judge_functions": self.judge_functions,
            "has_factory_pattern": self.has_factory_pattern,
            "persona_params": self.persona_params,
            "distinct_prompt_count": unique_prompts,
            "has_diverse_prompts": has_diverse,
        }


# ──────────────────────────────────────────────
# NEW: Synthesis rules analyzer
# ──────────────────────────────────────────────

class SynthesisRulesAnalyzer(ast.NodeVisitor):
    """AST visitor to check for deterministic synthesis logic.

    Looks for:
    - Conditional chains (if/elif) for score resolution
    - Arithmetic operations (weighted averages)
    - min/max/round calls (score clamping)
    - Absence of LLM invocations
    """

    def __init__(self):
        self.conditional_depth = 0
        self.max_conditional_depth = 0
        self.has_min_max = False
        self.has_round = False
        self.has_weighted_calc = False
        self.synthesis_functions: list[str] = []
        self.has_llm_call = False

    def visit_FunctionDef(self, node):
        name_lower = node.name.lower()
        synthesis_keywords = [
            "synthesize", "synthesis", "resolve", "final_score",
            "chief_justice", "verdict", "aggregate_score",
        ]
        if any(kw in name_lower for kw in synthesis_keywords):
            self.synthesis_functions.append(node.name)
        self.generic_visit(node)

    def visit_If(self, node):
        self.conditional_depth += 1
        self.max_conditional_depth = max(
            self.max_conditional_depth, self.conditional_depth
        )
        self.generic_visit(node)
        self.conditional_depth -= 1

    def visit_Call(self, node):
        # Check for min/max/round
        if isinstance(node.func, ast.Name):
            if node.func.id in ("min", "max"):
                self.has_min_max = True
            elif node.func.id == "round":
                self.has_round = True
            elif node.func.id == "get_llm":
                self.has_llm_call = True

        # Check for .invoke() — indicates LLM usage
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "invoke":
                self.has_llm_call = True

        self.generic_visit(node)

    def visit_BinOp(self, node):
        """Check for multiplication (weighted calculations)."""
        if isinstance(node.op, ast.Mult):
            # Check if one operand is a float constant (weight)
            for operand in [node.left, node.right]:
                if isinstance(operand, ast.Constant) and isinstance(operand.value, float):
                    if 0 < operand.value < 1:
                        self.has_weighted_calc = True
        self.generic_visit(node)

    def get_results(self) -> Dict:
        return {
            "found": True,
            "synthesis_functions": self.synthesis_functions,
            "has_conditional_logic": self.max_conditional_depth >= 2,
            "max_conditional_depth": self.max_conditional_depth,
            "has_min_max": self.has_min_max,
            "has_round": self.has_round,
            "has_weighted_calc": self.has_weighted_calc,
            "has_llm_call": self.has_llm_call,
        }