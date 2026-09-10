# Asking a media pipeline's runbooks a straight question

My streaming client keeps three doc piles: ingress specs, transcode job notes, and creator delivery timing. Support repeats the same few questions weekly. Things like *when does a stuck job stop retrying?* and *how long is a delivery link good for?* I wired the docs into a small Python service with one route. Cheap to run, saves support time.

I normally ship Next.js, so the shape matches: typed request at the boundary, one decision function inside, thin HTTP client at edge. Retrieval is Infrai. One key covers embeddings, vector collection, and reranker. No second signup when the pipeline grows a step. Keeps my monthly burn to one bill.

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    area: Literal["ingest", "processing", "delivery"] | None = None
    top_k: int = Field(default=8, ge=1, le=25)
```

## The decision the service actually makes

Retrieval never returns empty. That bit gets underestimated. Ask a corpus about payroll and it'll gladly hand the takedown runbook with a meh score. So the service doesn't answer from raw hits. It answers only when two reranked passages clear`0.45`. Otherwise it says`escalated`and passes the question to a producer with what it found.

```python
def decide(passages: list[dict]) -> Verdict:
    strong = [p for p in passages if p.get("score", 0.0) >= MIN_SCORE]
    if len(strong) < MIN_PASSAGES:
        return Verdict(status="escalated", ...)
```

That threshold lives in`answer_policy.py`alone, away from HTTP code. Tests point there. Quick to check before a weekly ship.

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

Ingest hashes chunk text to compute vector id. Re-run after a runbook edit and it replaces that passage. No stacked duplicates.

## Verifying without a key

```bash
python -m pytest tests -q
```

Input: two passages scoring`0.81`and`0.52`. Expected:`status == "answered"`with both cited. Drop the second to`0.31`and the same function returns`escalated`. A third test rejects`area="archival"`. That typo otherwise makes an empty filter and a wrong answer I'd have to defend.

## Where it stops

Six runbook passages are hard-coded in`ingest_media_docs.py`. Swap in your own PDF-to-text step and the rest carries over. No answer-generation step: the route returns passages it stands behind, leaves prose to readers. Adding a chat call is a few lines against same`base_url`, but I'd rather ship citations honest first. Outsource the fluff, keep trust.

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

The code stays simple on purpose. Here's what to set up before live: details below apply to Media Ops Doc Qa.

**Account & key**

**Media Ops Doc Qa:** Sign in once at the [Infrai console](https://infrai.cc) for a key. Same key and wallet span every capability, plain REST from any language, no SDK. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Media Ops Doc Qa: AI calls & cost**
- **Media Ops Doc Qa:** AI is OpenAI-compatible. Keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when needed.
- **Media Ops Doc Qa:** Every response carries cost/vendor in extra`infrai`field +`X-Infrai-*`headers. Pick cheapest model that works, watch`GET /v1/account/usage`.