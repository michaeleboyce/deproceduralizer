# Using Cascade Strategies - Quick Guide

Now you can choose between **rate-limited** and **error-driven** cascade strategies when running pipeline scripts!

## Smart Defaults

The factory automatically chooses the best strategy:

- **With `--workers > 1`**: Uses `rate_limited` (better for parallel processing)
- **Without workers**: Uses `error_driven` (better for sequential processing)
- **Can override**: Use `--cascade-strategy` to explicitly choose

```bash
# Auto-selects rate_limited (workers > 1)
./scripts/run-pipeline.sh --corpus=small --workers=8

# Auto-selects error_driven (no workers)
python pipeline/50_llm_reporting.py --in data.ndjson --out output.ndjson

# Explicit override
python pipeline/50_llm_reporting.py --cascade-strategy error_driven --in data.ndjson --out output.ndjson
```

## Backward Compatibility

Old parameter names are still supported:

```bash
# Old name: "extended" → maps to "rate_limited"
python pipeline/50_llm_reporting.py --cascade-strategy extended ...

# Old name: "simple" → maps to "rate_limited"
python pipeline/50_llm_reporting.py --cascade-strategy simple ...
```

The factory will automatically convert these and log the conversion.

## Command Line Usage

### Basic Usage

```bash
# Use error-driven cascade (default - recommended)
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting.ndjson \
  --cascade-strategy error_driven

# Use rate-limited cascade
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting.ndjson \
  --cascade-strategy rate_limited
```

### With Other Parameters

```bash
# Error-driven with limit
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting.ndjson \
  --cascade-strategy error_driven \
  --limit 100

# Rate-limited with parallel execution
python pipeline/35_llm_obligations.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/obligations.ndjson \
  --cascade-strategy rate_limited \
  --parallel
```

## Environment Variable Configuration

You can also set a default strategy via environment variable:

```bash
# Add to .env file
LLM_CASCADE_STRATEGY=error_driven

# Then run without --cascade-strategy flag
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting.ndjson
```

## Which Strategy to Use?

### Use **Error-Driven** (Default) When:
- ✅ You want maximum model utilization
- ✅ Rate limits are unknown or changing
- ✅ You prefer adaptive behavior
- ✅ You want successful models prioritized automatically

```bash
--cascade-strategy error_driven
```

**How it works:**
- Tries models until they actually error
- Failed models go to a retry queue
- Retries after 100 attempts (FIFO)
- Working models stay at top of stack

**Model Priority Order:**
1. **Vertex AI** (highest priority - Google AI Studio with higher limits)
   - gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash, gemini-2.0-flash-lite
2. **Gemini API** (backup tier - standard Google AI)
   - gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash, gemini-2.0-flash-lite
3. **Groq** (third tier - fast inference) - 9 models
4. **OpenRouter** (fourth tier - free tier) - 5 models
5. **Ollama** (final fallback - local) - phi4-mini

**Example output:**
```
✓ Added 4 Vertex models
✓ Added 4 Gemini models
✓ Added 9 Groq models
✓ Added 5 OpenRouter models
✓ Added Ollama fallback
🔄 Total models in cascade: 23

[Worker ThreadPoolExecutor-0_0] Trying vertex:gemini-2.5-flash for dc-1-101
⚠️  vertex:gemini-2.5-flash failed, moving to failed queue. Will retry after 100 attempts.

[Worker ThreadPoolExecutor-0_1] Trying gemini:gemini-2.5-flash for dc-1-102
🔄 Retrying vertex:gemini-2.5-flash (failed 1 times, 100 attempts since last failure)
✅ vertex:gemini-2.5-flash is working again! Moving to top of active stack.
```

**Worker Tracking:**
When using parallel workers (`--workers > 1` or `PIPELINE_WORKERS > 1`), logs show which worker is trying which model, making it easy to debug parallel execution.

### Use **Rate-Limited** When:
- ✅ You have accurate rate limit information
- ✅ You want to conserve API quota
- ✅ You prefer predictable, conservative behavior
- ✅ You need parallel execution within tiers

```bash
--cascade-strategy rate_limited
```

**How it works:**
- Checks rate limits before calling
- Fixed tier order: Gemini → Groq → OpenRouter → Ollama
- Retries higher tiers after 10 minutes
- Optional parallel execution (`--parallel`)

## Updated Scripts

The following pipeline scripts now support `--cascade-strategy`:

- ✅ `pipeline/50_llm_reporting.py`
- ✅ `pipeline/35_llm_obligations.py`
- ⚠️  `pipeline/60_llm_anachronisms.py` (update pending)

## Examples

### 1. Run reporting with error-driven cascade
```bash
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting_error_driven.ndjson \
  --cascade-strategy error_driven \
  --limit 50
```

### 2. Run obligations with rate-limited + parallel
```bash
python pipeline/35_llm_obligations.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/obligations_rate_limited.ndjson \
  --cascade-strategy rate_limited \
  --parallel \
  --limit 50
```

### 3. Use environment variable for default
```bash
# Set in .env
export LLM_CASCADE_STRATEGY=error_driven

# Run without flag (uses env default)
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/reporting.ndjson
```

## Monitoring Cascade Behavior

Both strategies provide detailed statistics at the end:

### Error-Driven Stats:
```
======================================================================
ERROR-DRIVEN CASCADE - LLM USAGE STATISTICS
======================================================================
Strategy: Error-driven with FIFO retry after 100 attempts
Session Duration: 5m 23s
Total Attempts: 150

Current Cascade Status:
  Active Models: gemini-2.5-flash, groq/compound, phi4-mini
  Failed Queue (2 models):
    - gemini-2.5-flash-lite: 1 failures, retry in 23 attempts
    - llama-3.3-70b: 2 failures, retry in 67 attempts

Model Usage:
  gemini-2.5-flash:
    ├─ Calls: 100 (66.7%)
    └─ Success Rate: 95.2% (100/105 attempts)
  groq/compound:
    ├─ Calls: 40 (26.7%)
    └─ Success Rate: 90.9% (40/44 attempts)
  phi4-mini:
    ├─ Calls: 10 (6.7%)
    └─ Success Rate: 100.0% (10/10 attempts)
======================================================================
```

### Rate-Limited Stats:
```
============================================================
LLM USAGE STATISTICS
============================================================
Cascade Strategy: extended
Session Duration: 5m 23s

Model Usage:
  gemini-2.5-flash: 100 calls (66.7%)
  groq/compound: 40 calls (26.7%)
  phi4-mini: 10 calls (6.7%)
  Total: 150 calls

Tier Performance:
  ├─ Gemini: 100 calls (3m 15s)
  ├─ Groq: 40 calls (1m 30s, 5 fallback periods)
  └─ Ollama: 10 calls (0m 38s, 2 fallback periods)

Tier Switches: 7 total
============================================================
```

## Testing

Test the strategies with a small dataset:

```bash
# Test error-driven
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/test_error_driven.ndjson \
  --cascade-strategy error_driven \
  --limit 20

# Test rate-limited
python pipeline/50_llm_reporting.py \
  --in data/outputs/sections_small.ndjson \
  --out data/outputs/test_rate_limited.ndjson \
  --cascade-strategy rate_limited \
  --limit 20

# Compare outputs
head -n 5 data/outputs/test_error_driven.ndjson
head -n 5 data/outputs/test_rate_limited.ndjson
```

## Help

Get help on any script:

```bash
python pipeline/50_llm_reporting.py --help
```

Output:
```
usage: 50_llm_reporting.py [-h] --in INPUT_FILE --out OUT [--limit LIMIT]
                           [--cascade-strategy {rate_limited,error_driven}]

Detect reporting requirements using LLM analysis

optional arguments:
  --cascade-strategy {rate_limited,error_driven}
                        LLM cascade strategy: 'rate_limited' (preemptive rate
                        limit checking) or 'error_driven' (reactive with FIFO
                        retry). Default: error_driven or LLM_CASCADE_STRATEGY
                        env var
```

---

**Quick Tip:** Start with `error_driven` (the default). It's more adaptive and will maximize your usage of available models!
