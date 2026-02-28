"""
General repository health and standards checking tools.
These checks are rubric-agnostic and work for any project structure.
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from src.state import Evidence


def check_readme(repo_path: Path) -> Dict:
    """Check for README.md file and assess its quality.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with README analysis
    """
    readme_paths = [
        repo_path / "README.md",
        repo_path / "README.rst",
        repo_path / "readme.md",
        repo_path / "Readme.md",
    ]
    
    readme_file = None
    for path in readme_paths:
        if path.exists():
            readme_file = path
            break
    
    if not readme_file:
        return {
            "found": False,
            "has_readme": False,
            "quality_score": 0.0,
            "sections": [],
            "error": "README file not found",
        }
    
    try:
        with open(readme_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for common README sections
        sections = []
        if re.search(r"#+\s*(installation|setup|getting started)", content, re.IGNORECASE):
            sections.append("installation")
        if re.search(r"#+\s*(usage|how to use|examples?)", content, re.IGNORECASE):
            sections.append("usage")
        if re.search(r"#+\s*(contributing|contribution)", content, re.IGNORECASE):
            sections.append("contributing")
        if re.search(r"#+\s*(license|licensing)", content, re.IGNORECASE):
            sections.append("license")
        if re.search(r"#+\s*(authors?|credits?)", content, re.IGNORECASE):
            sections.append("authors")
        if re.search(r"#+\s*(description|about|overview)", content, re.IGNORECASE):
            sections.append("description")
        
        # Quality score based on length and sections
        word_count = len(content.split())
        quality_score = min(1.0, (len(sections) * 0.15) + (min(word_count, 500) / 1000))
        
        return {
            "found": True,
            "has_readme": True,
            "quality_score": quality_score,
            "sections": sections,
            "word_count": word_count,
            "file_path": str(readme_file.relative_to(repo_path)),
        }
    except Exception as e:
        return {
            "found": True,
            "has_readme": True,
            "quality_score": 0.3,
            "sections": [],
            "error": f"Error reading README: {str(e)}",
        }


def check_gitignore(repo_path: Path) -> Dict:
    """Check for .gitignore file and assess its coverage.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with .gitignore analysis
    """
    gitignore_path = repo_path / ".gitignore"
    
    if not gitignore_path.exists():
        return {
            "found": False,
            "has_gitignore": False,
            "coverage_score": 0.0,
            "patterns": [],
            "error": ".gitignore not found",
        }
    
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        patterns = [line.strip() for line in content.split("\n") if line.strip() and not line.strip().startswith("#")]
        
        # Check for common important patterns
        important_patterns = [
            r"\.env",
            r"__pycache__",
            r"\.pyc",
            r"node_modules",
            r"\.venv",
            r"venv/",
            r"\.idea",
            r"\.vscode",
            r"dist/",
            r"build/",
        ]
        
        found_patterns = []
        for pattern in important_patterns:
            if any(re.search(pattern, p, re.IGNORECASE) for p in patterns):
                found_patterns.append(pattern)
        
        coverage_score = len(found_patterns) / len(important_patterns)
        
        return {
            "found": True,
            "has_gitignore": True,
            "coverage_score": coverage_score,
            "patterns": patterns,
            "important_patterns_found": found_patterns,
            "total_patterns": len(patterns),
        }
    except Exception as e:
        return {
            "found": True,
            "has_gitignore": True,
            "coverage_score": 0.3,
            "patterns": [],
            "error": f"Error reading .gitignore: {str(e)}",
        }


def check_license(repo_path: Path) -> Dict:
    """Check for LICENSE file.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with LICENSE analysis
    """
    license_paths = [
        repo_path / "LICENSE",
        repo_path / "LICENSE.txt",
        repo_path / "LICENSE.md",
        repo_path / "license",
        repo_path / "licence",
    ]
    
    license_file = None
    for path in license_paths:
        if path.exists():
            license_file = path
            break
    
    if not license_file:
        return {
            "found": False,
            "has_license": False,
        }
    
    try:
        with open(license_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Detect common licenses
        license_type = "unknown"
        if "MIT" in content or "MIT License" in content:
            license_type = "MIT"
        elif "Apache" in content or "Apache License" in content:
            license_type = "Apache"
        elif "GPL" in content or "GNU General Public License" in content:
            license_type = "GPL"
        elif "BSD" in content:
            license_type = "BSD"
        
        return {
            "found": True,
            "has_license": True,
            "license_type": license_type,
            "file_path": str(license_file.relative_to(repo_path)),
        }
    except Exception as e:
        return {
            "found": True,
            "has_license": True,
            "license_type": "unknown",
            "error": f"Error reading LICENSE: {str(e)}",
        }


def check_git_commit_standards(repo_path: Path) -> Dict:
    """Check git commit message standards and conventions.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with commit standards analysis
    """
    try:
        import subprocess
        
        # Get recent commit messages
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )
        
        if result.returncode != 0:
            return {
                "found": False,
                "error": "Could not retrieve git log",
            }
        
        commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        
        if not commits:
            return {
                "found": False,
                "error": "No commits found",
            }
        
        # Analyze commit message quality
        good_commits = 0
        issues = []
        
        for commit in commits:
            # Extract commit message (after hash)
            parts = commit.split(" ", 1)
            if len(parts) < 2:
                issues.append("Empty commit message")
                continue
            
            message = parts[1]
            
            # Check for common good practices
            is_good = True
            
            # Check length (not too short, not too long)
            if len(message) < 10:
                issues.append(f"Very short message: {message[:30]}")
                is_good = False
            elif len(message) > 72:
                issues.append(f"Very long message: {message[:30]}...")
                is_good = False
            
            # Check for imperative mood (good practice)
            if message[0].islower() and not message.startswith(("fix", "add", "update", "remove", "refactor", "improve")):
                # Not necessarily bad, but note it
                pass
            
            # Check for common prefixes (conventional commits)
            conventional_prefixes = ["fix:", "feat:", "docs:", "style:", "refactor:", "test:", "chore:"]
            has_prefix = any(message.lower().startswith(prefix) for prefix in conventional_prefixes)
            
            if is_good:
                good_commits += 1
        
        quality_score = good_commits / len(commits) if commits else 0.0
        
        return {
            "found": True,
            "total_commits_analyzed": len(commits),
            "good_commits": good_commits,
            "quality_score": quality_score,
            "issues": issues[:5],  # Limit to first 5 issues
            "sample_commits": commits[:5],
        }
    except Exception as e:
        return {
            "found": False,
            "error": f"Error analyzing commits: {str(e)}",
        }


def check_project_structure(repo_path: Path) -> Dict:
    """Check basic project structure and organization.
    
    Args:
        repo_path: Path to the cloned repository
        
    Returns:
        Dictionary with project structure analysis
    """
    structure_checks = {
        "has_src_directory": (repo_path / "src").exists() or (repo_path / "lib").exists() or (repo_path / "app").exists(),
        "has_tests_directory": (repo_path / "tests").exists() or (repo_path / "test").exists() or (repo_path / "__tests__").exists(),
        "has_docs_directory": (repo_path / "docs").exists() or (repo_path / "documentation").exists(),
        "has_config_file": any((repo_path / f).exists() for f in ["pyproject.toml", "setup.py", "package.json", "requirements.txt", "Pipfile"]),
    }
    
    score = sum(structure_checks.values()) / len(structure_checks)
    
    return {
        "found": True,
        "structure_checks": structure_checks,
        "organization_score": score,
    }


def check_general_repo_health(
    repo_path: Path,
    rubric_dimensions: List[Dict],
) -> List[Evidence]:
    """Run general repository health checks based on rubric dimensions.
    
    This function dynamically checks for common repository standards that
    might be relevant to any rubric dimension.
    
    Args:
        repo_path: Path to the cloned repository
        rubric_dimensions: List of rubric dimension dictionaries
        
    Returns:
        List of Evidence objects for general health checks
    """
    evidence_list = []
    
    # Always check README (universal standard)
    readme_result = check_readme(repo_path)
    evidence_list.append(Evidence(
        criterion_id="general_repo_health",
        goal="Check for README.md file and assess quality",
        found=readme_result.get("has_readme", False),
        location=str(repo_path / "README.md") if readme_result.get("found") else "not_found",
        content=json.dumps(readme_result),
        rationale=(
            f"README found with {len(readme_result.get('sections', []))} sections. "
            f"Quality score: {readme_result.get('quality_score', 0.0):.2f}"
            if readme_result.get("has_readme")
            else "README.md file not found"
        ),
        confidence=0.9 if readme_result.get("has_readme") else 0.1,
    ))
    
    # Always check .gitignore (universal standard)
    gitignore_result = check_gitignore(repo_path)
    evidence_list.append(Evidence(
        criterion_id="general_repo_health",
        goal="Check for .gitignore file and assess coverage",
        found=gitignore_result.get("has_gitignore", False),
        location=str(repo_path / ".gitignore") if gitignore_result.get("found") else "not_found",
        content=json.dumps(gitignore_result),
        rationale=(
            f".gitignore found with {gitignore_result.get('total_patterns', 0)} patterns. "
            f"Coverage: {gitignore_result.get('coverage_score', 0.0):.2f}"
            if gitignore_result.get("has_gitignore")
            else ".gitignore file not found"
        ),
        confidence=0.8 if gitignore_result.get("has_gitignore") else 0.2,
    ))
    
    # Check LICENSE (common standard)
    license_result = check_license(repo_path)
    evidence_list.append(Evidence(
        criterion_id="general_repo_health",
        goal="Check for LICENSE file",
        found=license_result.get("has_license", False),
        location=license_result.get("file_path", "not_found"),
        content=json.dumps(license_result),
        rationale=(
            f"LICENSE file found ({license_result.get('license_type', 'unknown')})"
            if license_result.get("has_license")
            else "LICENSE file not found"
        ),
        confidence=0.7 if license_result.get("has_license") else 0.3,
    ))
    
    # Check git commit standards
    commit_standards = check_git_commit_standards(repo_path)
    if commit_standards.get("found"):
        evidence_list.append(Evidence(
            criterion_id="general_repo_health",
            goal="Check git commit message standards",
            found=commit_standards.get("quality_score", 0.0) > 0.6,
            location=str(repo_path),
            content=json.dumps(commit_standards),
            rationale=(
                f"Commit quality score: {commit_standards.get('quality_score', 0.0):.2f}. "
                f"{commit_standards.get('good_commits', 0)}/{commit_standards.get('total_commits_analyzed', 0)} commits follow standards"
            ),
            confidence=commit_standards.get("quality_score", 0.5),
        ))
    
    # Check project structure
    structure_result = check_project_structure(repo_path)
    evidence_list.append(Evidence(
        criterion_id="general_repo_health",
        goal="Check basic project structure and organization",
        found=structure_result.get("organization_score", 0.0) > 0.5,
        location=str(repo_path),
        content=json.dumps(structure_result),
        rationale=(
            f"Organization score: {structure_result.get('organization_score', 0.0):.2f}. "
            f"Structure checks: {sum(structure_result.get('structure_checks', {}).values())}/{len(structure_result.get('structure_checks', {}))}"
        ),
        confidence=structure_result.get("organization_score", 0.5),
    ))
    
    return evidence_list



