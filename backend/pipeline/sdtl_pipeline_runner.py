from __future__ import annotations

import json
from pathlib import Path
import sys


from backend.drawing_analyzer.document_reader import PDFDocumentReader
from backend.drawing_analyzer.vector_extractor import VectorGeometryExtractor
from backend.drawing_analyzer.text_extractor import PDFTextExtractor
from backend.drawing_analyzer.dimension_detector import DimensionDetector
from backend.pipeline.geometry_report import GeometryReportBuilder


class SDTLPipelineRunner:
    """
    SDTL Integration Pipeline v0.1

    Primera etapa:
    PDF -> extracción -> reporte

    No genera objetos ni 3D todavía.
    """

    def __init__(self):

        self.document_reader = PDFDocumentReader()

        self.vector_extractor = VectorGeometryExtractor()

        self.text_extractor = PDFTextExtractor()

        self.dimension_detector = DimensionDetector()

        self.geometry_report = GeometryReportBuilder()


    def run(self, pdf_path: str):

        pdf = Path(pdf_path)

        if not pdf.exists():
            raise FileNotFoundError(pdf)


        print("=" * 60)
        print("SDTL PIPELINE v0.1")
        print("=" * 60)


        print(f"\nPDF:")
        print(pdf.name)


        #
        # 1. Documento
        #

        document = self.document_reader.read_document(
            str(pdf)
        )


        print("\nDocumento cargado")


        #
        # 2. Geometría vectorial
        #

        geometries = self.vector_extractor.extract_geometry(
            str(pdf)
        )


        print(
            f"Geometrías: {len(geometries)}"
        )


        #
        # Reporte geométrico detallado
        #

        geometry_report_path = self.geometry_report.build(
            entities=geometries,
            output_path="geometry_report.json",
            source_document=pdf.name
        )


        print(
            "\nReporte geométrico:"
        )

        print(
            geometry_report_path.absolute()
        )


        #
        # 3. Texto
        #

        texts = self.text_extractor.extract_text_with_coordinates(
            str(pdf)
        )


        print(
            f"Textos: {len(texts)}"
        )


        #
        # 4. Dimensiones
        #

        dimensions = self.dimension_detector.detect_dimensions(
          texts
        )


        print(
            f"Dimensiones: {len(dimensions)}"
        )


        #
        # Reporte inicial
        #

        result = {

            "pipeline":

            "SDTL v0.1",


            "source_pdf":

            pdf.name,


            "statistics":

            {

                "geometries":
                len(geometries),


                "texts":
                len(texts),


                "dimensions":
                len(dimensions)

            }

        }


        output = Path(
            "pipeline_output.json"
        )


        output.write_text(
            json.dumps(
                result,
                indent=4,
                default=str
            ),
            encoding="utf-8"
        )


        print("\nReporte generado:")
        print(output.absolute())


        return result



if __name__ == "__main__":


    if len(sys.argv) < 2:

        print(
            "Uso:"
        )

        print(
            "python -m backend.pipeline.sdtl_pipeline_runner <archivo.pdf>"
        )

        sys.exit(1)



    runner = SDTLPipelineRunner()


    runner.run(
        sys.argv[1]
    )