from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json
from datetime import datetime

from backend.drawing_analyzer.geometry_entity import GeometryEntity


class GeometryReportBuilder:
    """
    Generates traceable geometry extraction reports.

    This module does not modify geometry.
    It only summarizes extracted entities.
    """

    VERSION = "1.0"

    def build(
        self,
        entities: Iterable[GeometryEntity],
        output_path: str | Path,
        source_document: str | None = None,
    ) -> Path:

        entities = list(entities)

        entity_summary = []

        for entity in entities:

            entity_summary.append(
                {
                    "geometry_id": entity.geometry_id,
                    "document_id": entity.document_id,
                    "page_number": entity.page_number,
                    "entity_type": entity.entity_type,
                    "confidence": entity.confidence,
                    "coordinates": entity.coordinates,
                    "properties": entity.properties,
                }
            )


        report = {

            "sdtl_geometry_report":

                {
                    "version": self.VERSION,

                    "generated":

                        datetime.utcnow()
                        .isoformat(),

                    "source_document":
                        source_document,

                    "statistics":
                        {
                            "total_entities":
                                len(entities),

                            "entity_types":
                                self._count_types(
                                    entities
                                ),
                        },


                    "entities":
                        entity_summary
                }
        }


        output_path = Path(output_path)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )


        with output_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )


        return output_path


    def _count_types(
        self,
        entities: Iterable[GeometryEntity]
    ):

        result = {}

        for entity in entities:

            result[entity.entity_type] = (
                result.get(
                    entity.entity_type,
                    0
                )
                + 1
            )

        return result