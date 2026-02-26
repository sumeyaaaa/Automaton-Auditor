# Multi-Model Stack Configuration 🚀

## Overview

The Automaton Auditor uses an optimized multi-model stack to get the best results for each task:

## Model Assignments

### 1. ⚡ Grok-4-fast (xAI) - Repo Investigator
**Role**: Code analysis and Git forensic analysis  
**Node**: `repo_investigator_node`  
**Why**: Extremely fast for code analysis tasks, perfect for scanning repositories  
**Model**: `grok-2-fast` (or `grok-4-fast` if available)

### 2. 👁️ Gemini 2.5 Pro (Google) - Document & Vision Analysis
**Role**: PDF analysis and diagram classification  
**Nodes**: `doc_analyst_node`, `vision_inspector_node`  
**Why**: Massive context window, best-in-class for document understanding and multimodal analysis  
**Model**: `gemini-2.0-flash-exp` (or `gemini-2.5-pro`)

### 3. ⚖️ Grok-4-fast (xAI) - Judicial Bench
**Role**: Judicial debate and evaluation  
**Nodes**: `prosecutor_node`, `defense_node`, `tech_lead_node`  
**Why**: Extremely fast for parallel judicial debate, perfect for the courtroom  
**Model**: `grok-2-fast` (or `grok-4-fast` if available)

### 4. 🎯 Groq Llama 3.1 70B - Chief Justice
**Role**: Deterministic synthesis (doesn't actually use LLM, but kept for metadata)  
**Node**: `chief_justice_node`  
**Model**: `llama-3.1-70b-versatile`

## .env Configuration

```bash
# ============================================
# Repo Investigator - Grok-4-fast
# ============================================
XAI_API_KEY=your_xai_api_key_here
INVESTIGATOR_MODEL=grok-2-fast
INVESTIGATOR_PROVIDER=xai

# ============================================
# Document & Vision Analysis - Gemini 2.5 Pro
# ============================================
GOOGLE_API_KEY=your_google_api_key_here
LAYER1_MODEL=gemini-2.0-flash-exp
LAYER1_PROVIDER=google
VISUAL_MODEL=gemini-2.0-flash-exp
VISUAL_PROVIDER=google

# ============================================
# Judicial Bench - Grok-4-fast (xAI)
# ============================================
# XAI_API_KEY already set above for investigator
LAYER2_MODEL=grok-2-fast
LAYER2_PROVIDER=xai

# ============================================
# Chief Justice - Groq (optional, deterministic)
# ============================================
GROQ_API_KEY=your_groq_api_key_here
LAYER3_MODEL=llama-3.1-8b-instant
LAYER3_PROVIDER=groq
```

## Benefits of This Stack

### Speed ⚡
- **Grok-4-fast**: Instant code analysis
- **Groq**: 10x faster judicial debate (seconds instead of minutes)
- **Gemini**: Fast enough for document analysis, but quality > speed here

### Cost 💰
- **Groq**: Generous free tier
- **Gemini**: Free via Google AI Studio
- **Grok**: $20/month subscription (fast and reliable)

### Quality 🎯
- **Grok**: Excellent for code understanding
- **Gemini**: Best-in-class for documents and diagrams
- **Groq/Llama**: Great reasoning for judicial evaluation

## Installation

```bash
# Install all required packages
pip install langchain-groq langchain-google-genai langchain-xai

# Or with uv
uv sync
```

## Testing

```bash
# Test configuration
python -c "from src.config import get_model_metadata; import json; print(json.dumps(get_model_metadata(), indent=2))"

# Run audit
python -m src.graph "https://github.com/your-repo" "path/to/report.pdf"
```

## Rate Limits & Best Practices

1. **Groq**: Watch rate limits - don't spam too fast
2. **Gemini**: API keys can be region-sensitive
3. **Grok**: Fast and reliable, but paid subscription required

## Model Availability

- **grok-2-fast**: Available on xAI $20 subscription
- **gemini-2.0-flash-exp**: Available via Google AI Studio (free)
- **llama-3.1-70b-versatile**: Available on Groq (free tier)

