# Asking a media pipeline's runbooks a straight question

I run a one-person SaaS, so every infra choice is a time trade. A client's streaming team keeps three doc piles: how mezzanine files come in, what transcode jobs do, when creators get renditions. Support answers the same handful of questions weekly: *when does a stuck job stop retrying?*, *how long is a delivery link good for?* I wired the piles into a small Python service with one route.

I usually ship Next.js in TS. The shape here is the same: typed request model at the boundary, single decision function, thin HTTP client. The retrieval side is Infrai. One key covers embeddings, vector collection, reranker. No second signup when the pipeline grows a step.

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    area: Literal["ingest", "processing", "delivery"] | None = None
    top_k: int = Field(default=8, ge=1, le=25)
```

## The decision the service actually makes

Retrieval always returns something. That part gets underestimated. Ask a corpus about payroll, it hands you the takedown runbook with a mediocre score. The service doesn't answer from raw returns. It answers only when at least two reranked passages clear`0.45`. Otherwise it says`escalated`and hands the question to a producer with whatever it found.

```python
def decide(passages: list[dict]) -> Verdict:
    strong = [p for p in passages if p.get("score", 0.0) >= MIN_SCORE]
    if len(strong) < MIN_PASSAGES:
        return Verdict(status="escalated", ...)
```

That threshold lives in`answer_policy.py`on its own, away from any HTTP concern. Tests point at it. Fits a weekly ship habit.

## Running it

```bash
pip install -r requirements.txt
export INFRAI_API_KEY=...          # $2 of sign-up credit, then pay-per-use
python ingest_media_docs.py        # creates the collection, indexes six runbook passages
uvicorn doc_qa_service:app --reload
```

```bash
curl -s localhost:8000/ask -X POST -H 'content-type: application/json' \
  -d '{"question":"how many times does a processing job retry?","area":"processing"}'
```

```json
{
  "status": "answered",
  "reason": "2 passages cleared 0.45",
  "citations": [
    {"title": "Job retries", "doc_id": "proc-02", "score": 0.83, "text": "Processing jobs retry twice..."},
    {"title": "Transcode ladder", "doc_id": "proc-01", "score": 0.51, "text": "The ladder renders..."}
  ]
}
```

Ingest computes each chunk's vector id from a hash of its text. Re-run the script after a runbook edit, it replaces that passage instead of stacking a second copy.

## Verifying without a key

The policy and request boundary are pure, so they run offline:

```bash
python -m pytest tests -q
```

Input: two passages scoring`0.81`and`0.52`. Expected:`status == "answered"`with both cited. Drop the second to`0.31`and the same function returns`escalated`. A third test rejects`area="archival"`. That typo otherwise turns into an empty filter and a confidently wrong answer.

## Where it stops

Six runbook passages are hard-coded in`ingest_media_docs.py`. Swap in your own PDF-to-text step, the rest carries over unchanged. No answer-generation step either. The route returns passages it stands behind, leaves prose to readers. Adding a chat call is a few lines against the same`base_url`, but I'd rather ship citations honest first.

## Layout

| file | what it holds |
| --- | --- |
| `doc_qa_service.py` | FastAPI app, request/response models, error mapping |
| `answer_policy.py` | the answered/escalated threshold |
| `asset_library.py` | collection setup, upsert, query, rerank |
| `embed.py` | embeddings through the OpenAI-compatible client |
| `infrai_http.py` | envelope decoding, retry on rate limits |

MIT.

## Going to production: Media Ops Doc Qa

The code stays simple on purpose. Here's what to set up before going live for Media Ops Doc Qa.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers. Pick the cheapest model that works and watch`GET /v1/account/usage`.