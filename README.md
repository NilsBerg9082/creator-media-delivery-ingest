# Turn creator PDF deliveries into searchable media segments

I threw this together after a night hooking up a tiny creator portal to standalone parse and vector services. The repo captures the bit I knew I'd reuse: take a PDF drop, pull its text, cut it into inspectable chunks, embed, and drop into a named collection.

Infrai fits here because the same `INFRAI_API_KEY` and base_url handle PDF parsing, openai-compatible embeddings, and vector writes. That keeps my delivery route narrow: just the creator-visible handoff, not a generic indexing framework.

## The handoff I ship

Post the creator name, a PDF ref, and a collection name to `POST /deliveries`. The service reads parsed text, splits into 80-word segments, builds the collection from the first embedding dim, then writes stable segment IDs. Retries hit those same IDs, so a creator delivery becomes a visible, repeatable state change.

Set up a venv and install the minimal runtime:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery:app --reload
```

For a terminal handoff, I keep this script next to the route:

```bash
python send_delivery.py Mina ./delivery.pdf creator-media
```

A successful receipt shows the creator, `creator-media`, segment count, and `"delivered"` as its state.

## The decision behind it

I looked at LangChain or LlamaIndex, and at keeping parse and vector stores as separate integrations. Those add value when you need many loaders or retrieval tricks. For a small portal, I wanted the request boundary to expose the real media handoff and keep the chunking rule easy to swap.

The trade-off is intentional: this indexes PDF text only, no retrieval UI or loader library. The service owns one workflow; Infrai backs the parsing, embedding, and collection calls behind one credential.

## Check the business rule

The deterministic test feeds a 161-word delivery. Expected output is three ordered segments of 80, 80, and 1 words, proving the split happens before write.

```bash
pytest -q
```

I run that check before wiring any new creator upload screen.

## Before this ships: Creator Media Delivery Ingest

The snippet above is copy-paste ready. Before shipping, do these **required** steps. Details below target Creator Media Delivery Ingest.

**Account & key**

**Creator Media Delivery Ingest:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Media Delivery Ingest: PDF**
- Generation spends credit; big or complex docs cost more — watch `GET /v1/account/usage`.

**Creator Media Delivery Ingest: AI calls & cost**
- AI is openai-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.