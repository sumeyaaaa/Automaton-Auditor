# .env File Setup Guide - Groq (Llama) Configuration

## Quick Setup for Groq (Llama Models)

Your `.env` file should contain the following configuration:

```bash
# ============================================
# Groq API (Llama Models) - Fast & Affordable
# ============================================
# Get your API key from: https://console.groq.com
# Free tier available with generous limits!
GROQ_API_KEY=your_groq_api_key_here

# Model Configuration for Groq
# Available models:
# - llama-3.1-70b-versatile (best quality, recommended)
# - llama-3.1-8b-instant (faster, cheaper)
# - llama-3.3-70b-versatile (latest)
# - mixtral-8x7b-32768 (alternative)
LAYER1_MODEL=llama-3.1-70b-versatile
LAYER1_PROVIDER=groq
LAYER2_MODEL=llama-3.1-70b-versatile
LAYER2_PROVIDER=groq
LAYER3_MODEL=llama-3.1-70b-versatile
LAYER3_PROVIDER=groq

# ============================================
# Google Gemini API (for Visual/Multimodal)
# ============================================
# Get your API key from: https://makersuite.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Visual Model Configuration
VISUAL_MODEL=gemini-1.5-pro
VISUAL_PROVIDER=google
```

## Installation

Make sure you have the Groq package installed:
```bash
pip install langchain-groq
# or
uv sync
```

## Verification

Run this command to verify your configuration:
```bash
python -c "from src.config import get_model_metadata; import json; print(json.dumps(get_model_metadata(), indent=2))"
```

## Testing

After setting up your `.env` file with your GROQ_API_KEY, test with:
```bash
# Interim test (detectives only)
python -m src.graph "https://github.com/sumeyaaaa/Automaton-Auditor" "reports/interim_report.pdf" --interim

# Full audit (detectives + judges + synthesis)
python -m src.graph "https://github.com/sumeyaaaa/Automaton-Auditor" "reports/interim_report.pdf"
```

## Benefits of Groq

- ✅ **Fast inference** - Optimized for speed
- ✅ **Free tier available** - Generous free limits
- ✅ **Affordable** - Lower cost than many alternatives
- ✅ **Open-source models** - Llama models are transparent
- ✅ **Good for code analysis** - Llama models excel at technical tasks

## Model Recommendations

- **For quality**: `llama-3.1-70b-versatile` (default)
- **For speed/cost**: `llama-3.1-8b-instant`
- **For latest features**: `llama-3.3-70b-versatile`
