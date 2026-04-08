# ⚡ Quick Setup Guide

## 1. Clone & Install (2 min)

```bash
git clone <repo-url>
cd negotiation-env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configure Environment (1 min)

```bash
cp .env.example .env
# Edit .env and add HF_TOKEN
# Get token from: https://huggingface.co/settings/tokens
```

## 3. Verify Installation (1 min)

```bash
python -c "from environment import NegotiationEnvironment; from models import NegotiationAction; print('✓ All imports successful')"
```

## 4. Run Baseline Test (2 min)

```bash
python inference.py
```

Expected output:
```
[START] task=saas_renewal env=procurement-negotiation-env model=rule-based
[STEP] step=1 action=propose(110000) reward=0.05 done=False error=null
...
[END] success=true steps=3 score=0.583 rewards=0.05,0.08,0.42
```

## 5. Run LLM Agent (with GPU, ~3 min per task)

```bash
export HF_TOKEN=your_token_here
python inference_llm.py
```

Expected baseline:
- SaaS Renewal: 0.583
- Cloud Infrastructure: 0.744
- Enterprise Bundle: 1.000

## 6. Launch Interactive UI (optional)

```bash
bash start.sh
```

Open: http://localhost:7860

## 7. Docker (optional)

```bash
docker build -t negotiation-env:latest .
docker run -p 8000:8000 -p 7860:7860 -e HF_TOKEN=your_token negotiation-env:latest
```

---

## Checklist ✅

- [ ] Python 3.10+ installed
- [ ] HF_TOKEN obtained
- [ ] requirements.txt installed
- [ ] .env configured
- [ ] Imports verified
- [ ] Rule-based baseline runs
- [ ] LLM baseline runs (optional)
- [ ] Docker builds (optional)

---

## File Guide

| File | What It Does |
|------|---|
| `inference.py` | Rule-based baseline agent |
| `inference_llm.py` | LLM-based agent (Qwen2.5-72B) |
| `environment.py` | Negotiation simulator + vendor logic |
| `models.py` | Data validation (Pydantic) |
| `scenarios.py` | Task definitions |
| `graders.py` | Scoring functions |
| `server/app.py` | FastAPI endpoints |
| `gradio_ui.py` | Web UI |

---

## API Endpoints

### Reset (Start New Negotiation)
```bash
curl -X POST http://localhost:8000/reset \
  -H 'Content-Type: application/json' \
  -d '{"task":"saas_renewal","session_id":"test1"}'
```

### Step (Execute Action)
```bash
curl -X POST http://localhost:8000/step \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "test1",
    "action": {
      "move": "counter",
      "offer": {"price": 110000, "payment_terms": "net-60"},
      "justification": "Moving toward target"
    }
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

---

## Expected Baseline Scores

| Task | Rule-Based | LLM-Based |
|------|-----------|-----------|
| SaaS Renewal | ~0.45 | 0.583 |
| Cloud Infra | ~0.50 | 0.744 |
| Enterprise Bundle | ~0.30 | 1.000 |

Scores are from running the agent end-to-end without human intervention.

---

## Troubleshooting

**Q: "No API key provided" error**  
A: Set HF_TOKEN: `export HF_TOKEN=your_token_here`

**Q: "Connection refused" on /step**  
A: Start server: `uvicorn server.app:app --host 0.0.0.0 --port 8000`

**Q: Low scores**  
A: Check agent is creating valid offers. Enable verbose logging in `inference_llm.py`

**Q: LLM timeout**  
A: Check HF router is accessible. May need different API_BASE_URL.

---

For full documentation, see **README.md**
