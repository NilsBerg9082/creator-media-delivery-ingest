"""Run one creator delivery through the local service workflow."""

import argparse
import base64
from pathlib import Path

from media_delivery import DeliveryIngestor, DeliveryRequest, InfraiGateway


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("creator")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("collection")
    args = parser.parse_args()
    receipt = DeliveryIngestor(InfraiGateway.from_environment()).ingest(
        DeliveryRequest(
            creator=args.creator,
            source_pdf=base64.b64encode(args.pdf.read_bytes()).decode("ascii"),
            collection=args.collection,
        )
    )
    print(receipt.model_dump_json())


if __name__ == "__main__":
    main()
