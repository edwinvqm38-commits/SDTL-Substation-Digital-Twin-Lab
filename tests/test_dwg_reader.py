from __future__ import annotations

import os
import stat
from pathlib import Path

import ezdxf
import pytest

from backend.cad_reader import DWGConversionError, DWGConverter, DWGReader


def _make_fake_oda_converter(tmp_path: Path, template_dxf: Path) -> Path:
    """A stand-in for the real (license-gated, non-pip-installable) ODA File
    Converter binary that mimics its documented CLI contract: given an input
    folder and an output folder, "convert" every file in the input folder by
    copying a template DXF to <output>/<stem>.dxf. This lets us test
    DWGConverter's process invocation and output handling without the actual
    proprietary tool.
    """

    script = tmp_path / "fake_oda_converter.sh"
    script.write_text(
        "#!/bin/sh\n"
        'input_dir="$1"\n'
        'output_dir="$2"\n'
        'for f in "$input_dir"/*; do\n'
        '  stem=$(basename "$f")\n'
        '  stem="${stem%.*}"\n'
        f'  cp "{template_dxf}" "$output_dir/$stem.dxf"\n'
        "done\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


@pytest.fixture
def template_dxf(tmp_path: Path) -> Path:
    document = ezdxf.new()
    document.modelspace().add_line((0, 0), (10, 0))
    path = tmp_path / "template.dxf"
    document.saveas(path)
    return path


class TestDWGConverterAvailability:
    def test_not_available_without_installed_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ODA_FILE_CONVERTER_PATH", raising=False)
        monkeypatch.setattr("shutil.which", lambda name: None)

        converter = DWGConverter()

        assert converter.is_available is False

    def test_convert_raises_actionable_error_when_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("ODA_FILE_CONVERTER_PATH", raising=False)
        monkeypatch.setattr("shutil.which", lambda name: None)
        converter = DWGConverter()
        dwg_path = tmp_path / "plan.dwg"
        dwg_path.write_bytes(b"not a real dwg")

        with pytest.raises(DWGConversionError, match="opendesign.com"):
            converter.convert(dwg_path, tmp_path / "out")

    def test_resolves_executable_from_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_binary = tmp_path / "ODAFileConverter"
        fake_binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_binary.chmod(fake_binary.stat().st_mode | stat.S_IEXEC)
        monkeypatch.setenv("ODA_FILE_CONVERTER_PATH", str(fake_binary))

        converter = DWGConverter()

        assert converter.is_available is True
        assert converter.executable_path == fake_binary


class TestDWGConverterConversion:
    def test_converts_dwg_to_dxf_using_the_configured_binary(
        self, tmp_path: Path, template_dxf: Path
    ) -> None:
        fake_oda = _make_fake_oda_converter(tmp_path, template_dxf)
        converter = DWGConverter(executable_path=fake_oda)
        dwg_path = tmp_path / "SE-PI-PL-OC-500.dwg"
        dwg_path.write_bytes(b"fake dwg bytes")

        produced = converter.convert(dwg_path, tmp_path / "out")

        assert produced == tmp_path / "out" / "SE-PI-PL-OC-500.dxf"
        assert produced.is_file()

    def test_missing_dwg_file_raises_file_not_found(
        self, tmp_path: Path, template_dxf: Path
    ) -> None:
        fake_oda = _make_fake_oda_converter(tmp_path, template_dxf)
        converter = DWGConverter(executable_path=fake_oda)

        with pytest.raises(FileNotFoundError):
            converter.convert(tmp_path / "missing.dwg", tmp_path / "out")


class TestDWGReader:
    def test_reads_dwg_by_converting_then_delegating_to_dxf_reader(
        self, tmp_path: Path, template_dxf: Path
    ) -> None:
        fake_oda = _make_fake_oda_converter(tmp_path, template_dxf)
        reader = DWGReader(converter=DWGConverter(executable_path=fake_oda))
        dwg_path = tmp_path / "SE-PI-PL-OC-500.dwg"
        dwg_path.write_bytes(b"fake dwg bytes")

        document = reader.read(dwg_path, document_id="OC-500")

        assert document.document_id == "OC-500"
        assert document.filename == "SE-PI-PL-OC-500.dwg"
        assert document.metadata["converted_from_dwg"] is True
        assert document.metadata["source_path"] == str(dwg_path)
        assert document.statistics.total_entities == 1

    def test_read_document_alias_matches_read(
        self, tmp_path: Path, template_dxf: Path
    ) -> None:
        fake_oda = _make_fake_oda_converter(tmp_path, template_dxf)
        reader = DWGReader(converter=DWGConverter(executable_path=fake_oda))
        dwg_path = tmp_path / "plan.dwg"
        dwg_path.write_bytes(b"fake dwg bytes")

        document = reader.read_document(dwg_path)

        assert document.filename == "plan.dwg"
