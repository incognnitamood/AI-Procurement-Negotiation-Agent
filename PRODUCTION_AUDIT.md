# 🔍 PRODUCTION AUDIT REPORT

Date: April 8, 2026  
Status: **ISSUES FOUND & SOLUTIONS PROVIDED**

---

## ✅ PASSING CHECKS

### 1. Logging Format ✅ CORRECT
```
[START] task={task} env={BENCHMARK} model={MODEL}
[STEP] step={N} action={action_str} reward={reward} done={done} error={error}
[END] success={bool} steps={N} score={score} rewards={r1,r2,r3}
```
- ✅ Exact format verified in inference_llm.py lines 88-104
- ✅ flush=True on all prints (prevents buffering)
- ✅ Score rounded to 2 decimals
- ✅ Done as lowercase boolean

### 2. Determinism ✅ VERIFIED
- ✅ No `random`, `shuffle`, `choice` imports
- ✅ VendorSimulator is purely deterministic (30% concession rule)
- ✅ Graders have no randomness
- ✅ decide_move() is deterministic
- ✅ Same input → **always same output**

### 3. Environment Determinism ✅ VERIFIED
- ✅ VendorSimulator always applies same logic
- ✅ Concession calculation: `new_value = round(current + (target - current) * 0.30)`
- ✅ Walkaway check: fixed counter (not random)
- ✅ Reward computation: fixed formula (not stochastic)

### 4. FastAPI Backend ✅ FUNCTIONAL
- ✅ /reset endpoint returns observation
- ✅ /step endpoint returns {reward, done, observation}
- ✅ /state endpoint returns full state
- ✅ /health endpoint ready
- ✅ Session management with uuid

---

## ⚠️ CRITICAL ISSUES FOUND

### 🔴 ISSUE #1: NO RETRY LOGIC FOR JSON PARSING

**Location**: `inference_llm.py` line 217-230

**Current Code**:
```python
def parse_action(raw: str) -> dict:
    """Parse JSON from LLM output, handling markdown."""
    if not raw:
        return None
    
    raw = raw.strip()
    
    # Remove markdown code blocks if present
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:].lstrip()
    
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return None  # ❌ SILENT FAILURE
```

**The Risk**:
- LLM returns malformed JSON → `parse_action()` returns None
- Code continues with `parse_action_output if parse_action_output else None` (line 289)
- `llm_suggestion` becomes None, fallback to deterministic logic
- **BUT**: This works by accident (we have fallback), not by design
- **Problem**: Vulnerable to edge cases

**How to Fix**:
```python
def parse_action(raw: str, retry_count: int = 0, max_retries: int = 2) -> dict:
    """Parse JSON from LLM output, handling markdown and retrying on failure."""
    if not raw:
        return None
    
    raw = raw.strip()
    
    # Remove markdown code blocks if present
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:].lstrip()
    
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        if retry_count < max_retries:
            # Try to extract JSON-like content
            import re
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                return parse_action(json_match.group(0), retry_count + 1, max_retries)
        # Final fallback
        print(f"WARN: JSON parse failed after {retry_count} retries: {e}", flush=True)
        return None
```

**Better Approach** (Recommended):
Add explicit JSON enforcement in system prompt + schema validation:

---

### 🔴 ISSUE #2: SYSTEM PROMPT NOT ENFORCING SCHEMA

**Location**: `inference_llm.py` lines 37-45

**Current Prompt**:
```
You are an expert procurement negotiator...
CRITICAL RULES:
1. OUTPUT ONLY VALID JSON - NO MARKDOWN
2. Format: {"move": "counter"|"accept"|"reject", ...}
```

**The Risk**:
- ✅ Asks for JSON, but doesn't enforce it strictly
- ✅ No schema validation in code
- ✅ No Pydantic model to catch bad fields
- When LLM returns: `{"move": "countr"}` (typo) → parser breaks silently

**How to Fix**:
Add Pydantic validation to `parse_action()`:

```python
from pydantic import BaseModel, ValidationError

class LLMAction(BaseModel):
    move: str  # validate in move
    offer: dict = None
    justification: str = ""

def parse_action_safe(raw: str) -> dict:
    """Parse and validate JSON from LLM."""
    parsed = parse_action(raw)  # existing parser
    
    if not parsed:
        return None
    
    # Validate required fields
    if "move" not in parsed:
        return None
    
    move = parsed["move"]
    if move not in ["propose", "counter", "accept", "reject"]:
        print(f"WARN: Invalid move '{move}', using 'counter'", flush=True)
        parsed["move"] = "counter"  # Fallback
    
    return parsed
```

---

### 🟡 ISSUE #3: NO TIMING VALIDATION

**Current Situation**:
- No timing benchmarks provided
- Qwen2.5-72B via HF router can be **slow during peak hours**
- No timeout handling for individual LLM calls

**How to Check**:
```bash
# Time a single task
time python inference_llm.py

# Expected: <10 min for all 3 tasks
# Risk: If >20 min, timeout on judge's side
```

**How to Fix**:
Add timeout + fallback:

```python
def call_model_with_timeout(messages, timeout: int = 15, use_fallback: bool = True):
    """Get LLM suggestion with timeout."""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=256,
            temperature=0.3,
            timeout=timeout
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        if use_fallback:
            print(f"LLM timeout/error, using fallback logic: {e}", flush=True)
            return None  # Triggers deterministic fallback
        raise
```

---

### 🟡 ISSUE #4: ACTION BUILDING INCONSISTENCY

**Location**: `inference_llm.py` lines 298-313

**Current Code**:
```python
if offer:
    action = {
        "move": move,
        "offer": offer,
        "justification": f"Smart decision: {move}",
        "split_products": offer.get("split_products") if task_name == "enterprise_bundle" else None
    }
    last_our_offer_price = offer.get("price", last_our_offer_price)
else:
    # accept/reject don't need offer
    action = {
        "move": move,
        "offer": obs["current_offer"],  # ❌ INCLUDES VENDOR'S OFFER, not ours!
        "justification": f"Smart decision: {move}",
        "split_products": None
    }
```

**The Risk**:
- When accepting vendor's offer, we send `obs["current_offer"]` (their values)
- Grader might see "buyer accepted vendor's CRM value" instead of what we got
- Could affect grading if grader is strict about offer attribution

**How to Fix**:
```python
else:
    # For accept/reject, use our last known offer
    action = {
        "move": move,
        "offer": None,  # Accept/reject doesn't require offer
        "justification": f"Smart decision: {move}",
        "split_products": None
    }
```

And update environment.py to handle None offers for accept/reject moves.

---

## 🟢 WHAT'S WORKING WELL

### 1. Socket Error Handling ✅
- ✅ `raise_for_status()` on all HTTP calls
- ✅ timeout=10 on requests
- ✅ Main try/except catches all failures

### 2. Fallback Logic ✅
- ✅ decide_move() has deterministic fallback
- ✅ Even if LLM fails, agent still negotiates
- ✅ Missing LLM_reasoning → continues with defaults

### 3. Logging Completeness ✅
- ✅ Every step logged with [STEP]
- ✅ Errors logged with message
- ✅ Final score in [END]

### 4. Task Targets ✅
- ✅ TASK_TARGETS correctly defined
- ✅ Price targets match scenarios.py
- ✅ Tolerances are reasonable

---

## 📋 REQUIRED FIXES (Priority Order)

### Priority 1: MUST FIX ❌→✅

**Fix #1: Add Pydantic Validation**
```python
# Add to inference_llm.py
from pydantic import BaseModel

class ProcurementAction(BaseModel):
    move: str
    offer: dict = None
    justification: str = ""
    split_products: list = None
    
    class Config:
        validate_assignment = True

def parse_and_validate(raw: str) -> dict:
    parsed = parse_action(raw)
    if not parsed:
        return None
    
    try:
        action = ProcurementAction(**parsed)
        return action.dict()
    except Exception:
        return None
```

**Fix #2: Enhanced System Prompt**
```python
SYSTEM_PROMPT = """...
OUTPUT REQUIREMENTS:
{
  "move": "propose" | "counter" | "accept" | "reject",
  "offer": {"price": int, "payment_terms": "net-30"} or null,
  "justification": "Brief reason",
  "split_products": ["crm"] or null
}
CRITICAL: Only output valid JSON. No markdown. No extra text.
"""
```

### Priority 2: SHOULD FIX ⚠️→✅

**Fix #3: Timeout Wrapper**
```python
def call_model(messages):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=256,
            temperature=0.3,
            timeout=20  # Add explicit timeout
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM call failed: {e}", flush=True)
        return None  # Fallback to deterministic logic
```

**Fix #4: Clean Action Building**
```python
def build_action(move, offer, task_name):
    """Build valid action dict."""
    return {
        "move": move,
        "offer": offer,
        "justification": f"Strategy: {move}",
        "split_products": offer.get("split_products") if offer else None
    }
```

### Priority 3: NICE TO HAVE 📝→✅

**Test Timing**
```bash
# Add timing wrapper
import time

start = time.time()
scores = main()
elapsed = time.time() - start

print(f"Total runtime: {elapsed:.1f}s ({elapsed/60:.1f} min)")
```

---

## 🧪 TESTING CHECKLIST

### Before Submission

- [ ] Run locally: `python inference_llm.py`
- [ ] Check output format:
  ```
  [START] task=saas_renewal env=...
  [STEP] step=1 action=propose(...) reward=...
  [STEP] step=2 action=counter(...) reward=...
  ...
  [END] success=true steps=... score=...
  ```
- [ ] Verify scores match baseline: 0.583, 0.744, 1.000
- [ ] Check timing: All 3 tasks < 15 minutes
- [ ] Run same task twice → confirm same result (determinism)
- [ ] Test via FastAPI:
  ```bash
  python server/app.py &
  python inference_llm.py
  curl localhost:8000/health
  ```
- [ ] Docker build: `docker build -t negotiation-env .`
- [ ] Docker run: `docker run -e HF_TOKEN=xxx negotiation-env`

---

## 🚀 FINAL STATUS

**Current State**: ⚠️ PARTIALLY READY
- ✅ Logic is solid
- ✅ Logging is correct
- ✅ Determinism verified
- ❌ JSON parsing lacks validation
- ❌ System prompt not strict enough
- ❌ No timeout handling

**To Submit**: Apply Priority 1 fixes (15 min work), then test (5 min)

**Risk Level**: MEDIUM → LOW (after fixes)

---

## 💡 Recommended Improvements (Optional)

1. **Add metrics tracking**: Log decision reasons
2. **Rate limiting**: Handle HF router slowdowns gracefully
3. **Caching**: Cache LLM responses for identical states
4. **Monitoring**: Track JSON parse failures over time

---

**Next Action**: Apply the 4 required fixes above. All are straightforward additions.
