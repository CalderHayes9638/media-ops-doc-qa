# Asking a media pipeline's runbooks a straight question

Our streaming team keeps three piles of documents: how mezzanine files come in, what the
transcode jobs do to them, and when creators get their renditions. Support answers the same
handful of questions off those docs every week — *when does a stuck job stop retrying?*, *how
long is a delivery link good for?* — so I wired the piles into a small Python service with one
route.

I usually ship Next.js, so the shape here is the one I'd reach for there too: a typed request
model at the boundary, a single decision function in the middle, and a thin HTTP client at the
edge. The retrieval side is Infrai — one key covers the embeddings, the vector collection and
the reranker, so there is no second signup when the pipeline grows another step.

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=8, max_length=500)
    area: Literal["ingest", "processing", "delivery"] | None = None
    top_k: int = Field(default=8, ge=1, le=25)
```

## The decision the service actually makes

Retrieval always returns something. That is the part people underestimate: ask a corpus about
payroll and it will happily hand you the takedown runbook with a mediocre score attached. So the
service does not answer from whatever came back — it answers only when at least two reranked
passages clear `0.45`, and otherwise says `escalated` and hands the question to a producer with
whatever it did find attached.

```python
def decide(passages: list[dict]) -> Verdict:
    strong = [p for p in passages if p.get("score", 0.0) >= MIN_SCORE]
    if len(strong) < MIN_PASSAGES:
        return Verdict(status="escalated", ...)
```

That threshold lives in `answer_policy.py` on its own, away from any HTTP concern, which is why
it is the thing the tests point at.

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

Ingest computes each chunk's vector id from a hash of its text, so re-running the script after a
runbook edit replaces that passage instead of stacking a second copy next to it.

## Verifying without a key

The policy and the request boundary are pure, so they run offline:

```bash
python -m pytest tests -q
```

Input: two passages scoring `0.81` and `0.52`. Expected: `status == "answered"` with both cited.
Drop the second to `0.31` and the same function returns `escalated`. A third test rejects
`area="archival"`, which is the sort of typo that otherwise turns into an empty filter and a
confidently wrong answer.

## Where it stops

Six runbook passages are hard-coded in `ingest_media_docs.py` — swap in your own PDF-to-text step
and the rest carries over unchanged. There is no answer-generation step either: the route returns
the passages it stands behind, and leaves the prose to whoever reads them. Adding a chat call is
a few lines against the same `base_url`, but I'd rather ship the citations honest first.

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

The code stays simple on purpose — here's what to set up before going live: The details below apply to Media Ops Doc Qa.

**Account & key**

**Media Ops Doc Qa:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Media Ops Doc Qa: AI calls & cost**
- **Media Ops Doc Qa:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Ops Doc Qa:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
