"""
AST-based code analysis tools.
Uses Python's ast module (not regex) for structural code verification.
"""
import ast
from pathlib import Path
from typing import Dict, List, Optional


def check_stategraph(repo_path: Path) -> Dict:
    """Check for LangGraph StateGraph instantiation using AST.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with StateGraph analysis results
    """
    graph_file = repo_path / "src" / "graph.py"
    if not graph_file.exists():
        # Try alternative locations
        graph_file = repo_path / "graph.py"
        if not graph_file.exists():
            return {
                "found": False,
                "error": "graph.py not found",
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
    state_file = repo_path / "src" / "state.py"
    if not state_file.exists():
        # Try alternative locations
        state_file = repo_path / "state.py"
        if not state_file.exists():
            return {
                "found": False,
                "has_pydantic": False,
                "has_reducers": False,
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
    graph_file = repo_path / "src" / "graph.py"
    if not graph_file.exists():
        graph_file = repo_path / "graph.py"
        if not graph_file.exists():
            return {
                "found": False,
                "has_parallel_edges": False,
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
            
            # AST-based check for tempfile usage
            try:
                tree = ast.parse(content)
                tempfile_checker = SandboxingAnalyzer()
                tempfile_checker.visit(tree)
                if tempfile_checker.has_tempfile:
                    has_sandboxing = True
            except:
                pass
            
            # Check for forbidden patterns
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
    judges_file = repo_path / "src" / "nodes" / "judges.py"
    if not judges_file.exists():
        return {
            "found": False,
            "has_structured_output": False,
        }

    try:
        with open(judges_file, "r", encoding="utf-8") as f:
            source_code = f.read()
        
        # AST-based check
        tree = ast.parse(source_code)
        analyzer = StructuredOutputAnalyzer()
        analyzer.visit(tree)
        
        # Also check for string patterns
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
            
            # Check for forbidden patterns
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


# AST Analyzer Classes


class StateGraphAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze LangGraph StateGraph structure."""

    def __init__(self):
        self.has_stategraph = False
        self.has_parallel_edges = False
        self.has_conditional_edges = False
        self.node_names = []
        self.edge_patterns = []

    def visit_ImportFrom(self, node):
        """Check for StateGraph import."""
        if node.module == "langgraph.graph" or node.module == "langgraph":
            for alias in node.names:
                if alias.name == "StateGraph":
                    self.has_stategraph = True
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check for graph builder patterns."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_edge":
                self.has_parallel_edges = True
                # Try to extract edge information
                if len(node.args) >= 2:
                    self.edge_patterns.append({
                        "from": self._extract_name(node.args[0]),
                        "to": self._extract_name(node.args[1]),
                    })
            elif node.func.attr == "add_conditional_edges":
                self.has_conditional_edges = True
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Extract node names."""
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Attribute):
                if node.value.func.attr == "add_node":
                    if len(node.value.args) > 0:
                        node_name = self._extract_name(node.value.args[0])
                        if node_name:
                            self.node_names.append(node_name)
        self.generic_visit(node)

    def _extract_name(self, node) -> Optional[str]:
        """Extract string name from AST node."""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return str(node.value) if isinstance(node.value, str) else None
        elif isinstance(node, ast.Name):
            return node.id
        return None

    def get_results(self) -> Dict:
        """Get analysis results."""
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
        """Check for Pydantic and TypedDict imports."""
        if node.module == "pydantic":
            self.has_pydantic = True
        elif node.module == "typing" or node.module == "typing_extensions":
            for alias in node.names:
                if alias.name == "TypedDict":
                    self.has_typeddict = True
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Check for Evidence and JudicialOpinion classes."""
        if "Evidence" in node.name:
            self.has_evidence = True
        if "JudicialOpinion" in node.name or "Opinion" in node.name:
            self.has_judicial_opinion = True
        
        # Check for BaseModel inheritance
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                self.has_pydantic = True
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        """Check for Annotated reducers."""
        if isinstance(node.annotation, ast.Subscript):
            if isinstance(node.annotation.value, ast.Name):
                if node.annotation.value.id == "Annotated":
                    # Check for operator imports
                    self.has_reducers = True
        self.generic_visit(node)

    def get_results(self) -> Dict:
        """Get analysis results."""
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
        """Check for add_edge calls."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_edge":
                if len(node.args) >= 2:
                    from_node = self._extract_name(node.args[0])
                    to_node = self._extract_name(node.args[1])
                    self.edge_calls.append((from_node, to_node))
        self.generic_visit(node)

    def _extract_name(self, node) -> Optional[str]:
        """Extract string name from AST node."""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return str(node.value) if isinstance(node.value, str) else None
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):  # List-style join edges
            return f"[{len(node.elts)} nodes]"
        return None

    def get_results(self) -> Dict:
        """Get analysis results."""
        # Check for fan-out (multiple edges from same source)
        from_nodes = {}
        for from_node, to_node in self.edge_calls:
            if from_node not in from_nodes:
                from_nodes[from_node] = []
            from_nodes[from_node].append(to_node)
        
        # Fan-out: same source -> multiple destinations
        for from_node, to_nodes in from_nodes.items():
            if len(to_nodes) > 1:
                self.has_fan_out = True
        
        # Fan-in: multiple sources -> same destination
        to_nodes = {}
        for from_node, to_node in self.edge_calls:
            if to_node not in to_nodes:
                to_nodes[to_node] = []
            to_nodes[to_node].append(from_node)
        
        for to_node, from_nodes_list in to_nodes.items():
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
        """Check for tempfile import."""
        if node.module == "tempfile":
            self.has_tempfile = True
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check for TemporaryDirectory calls."""
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
        """Check for with_structured_output calls."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "with_structured_output":
                self.has_structured_output = True
            elif node.func.attr == "bind_tools":
                self.has_structured_output = True
        self.generic_visit(node)

