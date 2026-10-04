import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import send_delivery
from delivery_logic import split_delivery
from media_delivery import DeliveryReceipt, InfraiGateway


def test_creator_delivery_is_chunked_before_it_is_upserted() -> None:
    delivery = " ".join(f"word{number}" for number in range(161))

    segments = split_delivery(delivery)

    assert len(segments) == 3
    assert [len(segment.split()) for segment in segments] == [80, 80, 1]


def test_pdf_parse_joins_page_text() -> None:
    gateway = InfraiGateway("test-key")
    gateway._send = lambda method, path, body: {
        "pages": [{"page": 1, "text": "First page"}, {"page": 2, "text": "Second page"}]
    }

    assert gateway.parse_pdf("encoded-pdf") == "First page\n\nSecond page"


def test_cli_encodes_a_local_pdf(monkeypatch, tmp_path, capsys) -> None:
    pdf_path = tmp_path / "delivery.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    captured = {}

    class FakeGateway:
        @classmethod
        def from_environment(cls):
            return cls()

    class FakeIngestor:
        def __init__(self, gateway):
            pass

        def ingest(self, request):
            captured["request"] = request
            return DeliveryReceipt(
                creator=request.creator,
                collection=request.collection,
                segment_count=1,
                state="delivered",
            )

    monkeypatch.setattr(send_delivery, "InfraiGateway", FakeGateway)
    monkeypatch.setattr(send_delivery, "DeliveryIngestor", FakeIngestor)
    monkeypatch.setattr(sys, "argv", ["send_delivery.py", "Mina", str(pdf_path), "creator-media"])

    send_delivery.main()

    assert captured["request"].source_pdf == base64.b64encode(b"%PDF-test").decode("ascii")
    assert '"state":"delivered"' in capsys.readouterr().out
