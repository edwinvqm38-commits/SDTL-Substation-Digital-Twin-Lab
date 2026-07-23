from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .extraction_pipeline import DrawingToObjectsPipeline
from .generate_3d import ThreeDGenerationStage
from .quantity_takeoff import QuantityTakeoffBuilder
from .review_queue import ReviewQueue


class SDTLPipelineRunner:
    """SDTL Integration Pipeline v2.0

    Connects the previously separate extraction, semantic, object-generation,
    3D-generation, and quantity-takeoff stages into one traceable flow:

        PDF -> geometries/text/dimensions -> engineering candidates
            -> reviewable SDTL objects (review_queue.json)
            -> [human approval]
            -> 3D models (glTF) + quantity takeoff (metrado_report.json)

    Object approval is intentionally a separate, explicit step (see the
    `approve` subcommand) -- no stage here ever marks an object approved.
    """

    def __init__(self) -> None:
        self.extraction = DrawingToObjectsPipeline()
        self.review_queue = ReviewQueue()
        self.generation = ThreeDGenerationStage()
        self.takeoff = QuantityTakeoffBuilder()

    def extract(self, pdf_path: str, output_dir: str) -> Path:
        result = self.extraction.run(pdf_path)
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        queue_path = self.review_queue.save(result.objects, output / "review_queue.json")

        report = {
            "pipeline": "SDTL v2.0",
            "source_pdf": result.source_pdf,
            "statistics": result.statistics,
            "review_queue": str(queue_path),
            "skipped_candidates": [
                {
                    "candidate_id": item.candidate_id,
                    "possible_type": item.possible_type,
                    "confidence": item.confidence,
                    "reason": item.reason,
                }
                for item in result.skipped
            ],
        }
        report_path = output / "extraction_report.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Objetos generados (pendientes de revision): {len(result.objects)}")
        print(f"Candidatos descartados: {len(result.skipped)}")
        print(f"Cola de revision: {queue_path}")
        print(f"Reporte: {report_path}")
        return report_path

    def approve(self, queue_path: str, object_id: str, reviewer: str) -> None:
        obj = self.review_queue.approve(queue_path, object_id, reviewer)
        print(f"{obj.id} ({obj.type}) aprobado por {reviewer}; estado: {obj.state}")

    def generate_3d(self, queue_path: str, output_dir: str) -> Path:
        objects = self.review_queue.load(queue_path)
        result = self.generation.run(objects, output_dir)

        manifest = {
            "generated": [
                {
                    "object_id": item.object_id,
                    "object_type": item.object_type,
                    "gltf_path": str(item.gltf_path),
                }
                for item in result.generated
            ],
            "skipped": result.skipped,
        }
        manifest_path = Path(output_dir) / "generation_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Modelos 3D generados: {len(result.generated)}")
        print(f"Omitidos: {len(result.skipped)}")
        print(f"Manifiesto: {manifest_path}")
        return manifest_path

    def quantity_takeoff(self, queue_path: str, output_path: str) -> Path:
        objects = self.review_queue.load(queue_path)
        report = self.takeoff.build(objects)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Metrado: {target}")
        return target


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SDTL pipeline v2.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="PDF -> reviewable SDTL objects")
    extract_parser.add_argument("pdf_path")
    extract_parser.add_argument("--output-dir", default="pipeline_output")

    approve_parser = subparsers.add_parser("approve", help="Approve one object in a review queue")
    approve_parser.add_argument("queue_path")
    approve_parser.add_argument("object_id")
    approve_parser.add_argument("reviewer")

    generate_parser = subparsers.add_parser("generate3d", help="Approved objects -> glTF")
    generate_parser.add_argument("queue_path")
    generate_parser.add_argument("--output-dir", default="pipeline_output/models")

    takeoff_parser = subparsers.add_parser("takeoff", help="Approved objects -> metrado report")
    takeoff_parser.add_argument("queue_path")
    takeoff_parser.add_argument("--output-path", default="pipeline_output/metrado_report.json")

    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args(sys.argv[1:])
    runner = SDTLPipelineRunner()

    if args.command == "extract":
        runner.extract(args.pdf_path, args.output_dir)
    elif args.command == "approve":
        runner.approve(args.queue_path, args.object_id, args.reviewer)
    elif args.command == "generate3d":
        runner.generate_3d(args.queue_path, args.output_dir)
    elif args.command == "takeoff":
        runner.quantity_takeoff(args.queue_path, args.output_path)
