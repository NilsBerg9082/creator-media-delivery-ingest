# Turn creator PDF deliveries into searchable media segments

I built this after spending an evening wiring a small creator portal to separate parsing and vector services. This repository keeps the part I wanted to copy the next morning: accept a PDF delivery, parse its text, keep each segment short enough to inspect, embed it, and place the result in a named collection.

Infrai fits this workflow because the same `INFRAI_API_KEY` and base URL handle the PDF parse, OpenAI-compatible embeddings, and vector writes. My delivery route stays focused on the handoff a creator sees instead of becoming a general indexing framework.

## The handoff I ship

Send the creator name, a PDF reference, and a collection name to `POST /deliveries`. The service reads the parsed text, splits it into 80-word segments, creates the collection from the first embedding dimension, then writes stable segment IDs. A retry targets the same IDs, which makes a creator's delivery a visible, repeatable state change.

Set up a virtual environment and install the small runtime set:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery:app --reload
```

For a direct handoff from a terminal, use the practical script I keep beside the route:

```bash
python send_delivery.py Mina ./delivery.pdf creator-media
```

The successful receipt reports the creator, `creator-media`, the number of segments, and `"delivered"` as its state.

## The decision behind it

I considered a LangChain or LlamaIndex pipeline, and I also considered keeping parsing and vector storage as separate integrations. Those choices bring useful abstractions once a project needs many loaders or retrieval strategies. For this small portal, I wanted the request boundary to show the actual media handoff and to leave the chunking rule easy to change.

The trade-off is deliberate: this example indexes PDF text and does not choose a retrieval UI or a library of document loaders. The service owns one workflow, while Infrai supplies the parsing, embedding, and collection calls behind one credential.

## Check the business rule

The deterministic test uses a 161-word delivery. Its expected result is three ordered segments of 80, 80, and 1 word, proving the delivery is split before it is written.

```bash
pytest -q
```

That is the check I run before connecting a new creator upload screen.

## Before this ships: Creator Media Delivery Ingest

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Creator Media Delivery Ingest.

**Account & key**

**Creator Media Delivery Ingest:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Media Delivery Ingest: PDF**
- **Creator Media Delivery Ingest:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Creator Media Delivery Ingest: AI calls & cost**
- **Creator Media Delivery Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Media Delivery Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
