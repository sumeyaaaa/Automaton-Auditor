# How to Get LangSmith Trace Link

This guide explains how to set up LangSmith tracing and retrieve the trace link for your audit runs.

## Step 1: Get LangSmith API Key

1. **Sign up/Login to LangSmith**:
   - Go to: https://smith.langchain.com
   - Sign up for a free account (if you don't have one)
   - Or login with your existing account

2. **Create an API Key**:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Give it a name (e.g., "automaton-auditor")
   - Copy the API key (starts with `lsv2_pt_...` or `lsv2_sk_...`)

## Step 2: Configure Environment Variables

1. **Open your `.env` file** (create it from `.env.example` if needed):
   ```bash
   cp .env.example .env
   ```

2. **Add LangSmith configuration**:
   ```bash
   # Enable LangSmith tracing
   LANGCHAIN_TRACING_V2=true
   
   # Your LangSmith API key (from Step 1)
   LANGCHAIN_API_KEY=lsv2_pt_your_actual_key_here
   
   # Project name (optional, but recommended for organization)
   LANGCHAIN_PROJECT=automaton-auditor
   ```

3. **Save the `.env` file**

## Step 3: Run an Audit with Tracing Enabled

Run a full audit (this will automatically create traces in LangSmith):

```bash
python -m src.graph https://github.com/sumeyaaaa/Automaton-Auditor reports/final_report.pdf
```

Or for a peer audit:

```bash
python -m src.graph https://github.com/Abnet-Melaku1/automation-auditor reports/interim_report.pdf
```

**Note**: 
- The tracing happens automatically when `LANGCHAIN_TRACING_V2=true` is set. You don't need to do anything special - just run the audit normally.
- The system supports both PDF (`.pdf`) and Markdown (`.md`) report formats. Use the appropriate file path for your report.

## Step 4: Find Your Trace Link

### Option A: From LangSmith Dashboard (Recommended)

1. **Go to LangSmith Dashboard**:
   - Visit: https://smith.langchain.com
   - Login if needed

2. **Navigate to Projects**:
   - Click on "Projects" in the left sidebar
   - Select "automaton-auditor" (or the project name you set in `.env`)

3. **Find Your Latest Run**:
   - You'll see a list of runs (each audit execution creates a run)
   - The most recent run will be at the top
   - Each run shows:
     - Timestamp
     - Duration
     - Status (Success/Error)

4. **Click on the Run**:
   - Click on the run you want to share
   - This opens the detailed trace view

5. **Copy the Trace URL**:
   - The URL in your browser is the trace link!
   - Example: `https://smith.langchain.com/o/YOUR_ORG_ID/projects/p/YOUR_PROJECT_ID/runs/YOUR_RUN_ID`
   - Copy this URL - this is what you'll submit

### Option B: From Command Line Output

When you run an audit, LangSmith may print trace information. Look for output like:

```
[LangSmith] Run: https://smith.langchain.com/o/.../runs/...
```

However, this is not always displayed, so **Option A (Dashboard) is more reliable**.

## Step 5: Verify Your Trace

Before submitting, verify your trace shows:

1. **Detectives collecting evidence**:
   - `repo_investigator_node` with tool calls
   - `doc_analyst_node` with PDF parsing
   - `vision_inspector_node` (if enabled)

2. **Judges deliberating in parallel**:
   - `prosecutor_node` with LLM calls
   - `defense_node` with LLM calls
   - `tech_lead_node` with LLM calls
   - All should show parallel execution

3. **Chief Justice synthesizing**:
   - `chief_justice_node` with synthesis logic
   - Final report generation

4. **Complete flow**:
   - START → context_builder
   - → [3 detectives in parallel]
   - → evidence_aggregator
   - → [3 judges in parallel]
   - → chief_justice
   - → END

## Step 6: Share the Trace Link

1. **Copy the full URL** from your browser when viewing the trace
2. **Test the link** by opening it in an incognito/private window (to ensure it's shareable)
3. **Include in your submission**:
   - Add to your PDF report
   - Or include in submission form/email

## Troubleshooting

### No traces appearing?

1. **Check environment variables**:
   ```bash
   # Verify they're loaded
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Tracing:', os.getenv('LANGCHAIN_TRACING_V2')); print('API Key:', 'Set' if os.getenv('LANGCHAIN_API_KEY') else 'Missing')"
   ```

2. **Verify API key is correct**:
   - Make sure there are no extra spaces
   - Make sure it starts with `lsv2_pt_` or `lsv2_sk_`

3. **Check LangSmith dashboard**:
   - Sometimes traces take a few seconds to appear
   - Refresh the dashboard after running an audit

### Can't find your project?

- If you didn't set `LANGCHAIN_PROJECT`, traces go to "default" project
- Check "default" project in LangSmith dashboard
- Or set `LANGCHAIN_PROJECT=automaton-auditor` in `.env` and run again

### Trace link not working?

- Make sure you're logged into LangSmith
- The link should work for anyone with access to your LangSmith organization
- If sharing publicly, you may need to make the project public in settings

## Quick Reference

**Required Environment Variables**:
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key_here
LANGCHAIN_PROJECT=automaton-auditor  # Optional but recommended
```

**Where to get API key**: https://smith.langchain.com → Settings → API Keys

**Where to find traces**: https://smith.langchain.com → Projects → automaton-auditor → Click on run

**Example trace URL format**:
```
https://smith.langchain.com/o/[ORG_ID]/projects/p/[PROJECT_ID]/runs/[RUN_ID]
```

---

**Need Help?** Check LangSmith documentation: https://docs.smith.langchain.com/

