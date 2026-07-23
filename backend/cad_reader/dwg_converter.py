from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

_INSTALL_MESSAGE = (
    "ODA File Converter is not installed or was not found. It is a free tool "
    "from the Open Design Alliance, but it is a separate, license-gated "
    "download this project cannot bundle or auto-install: "
    "https://www.opendesign.com/guestfiles/oda_file_converter . After "
    "installing it, either add it to PATH as 'ODAFileConverter' or set the "
    "ODA_FILE_CONVERTER_PATH environment variable to its executable path."
)


class DWGConversionError(RuntimeError):
    """Raised when ODA File Converter is missing or a DWG conversion fails."""


class DWGConverter:
    """Convert a DWG file to DXF via the ODA File Converter CLI so it can be
    read with the existing, already-tested DXFReader.

    This class only wraps the external tool's batch-folder CLI contract; it
    performs no DWG parsing itself.
    """

    _DEFAULT_EXECUTABLE_NAMES = ("ODAFileConverter", "ODAFileConverter.exe")

    def __init__(
        self,
        executable_path: str | Path | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.executable_path = self._resolve_executable(executable_path)
        self.timeout = timeout

    @property
    def is_available(self) -> bool:
        return self.executable_path is not None

    def convert(
        self,
        dwg_path: str | Path,
        output_dir: str | Path,
        output_version: str = "ACAD2018",
    ) -> Path:
        """Convert one DWG file to DXF and return the produced .dxf path."""

        if self.executable_path is None:
            raise DWGConversionError(_INSTALL_MESSAGE)

        source = Path(dwg_path)
        if not source.is_file():
            raise FileNotFoundError(f"DWG file not found: {source}")

        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)

        # The converter's CLI only operates on whole folders, not a single
        # file, so stage this one input in an isolated temp directory to
        # avoid converting unrelated files that might sit next to it.
        with tempfile.TemporaryDirectory() as staging_dir:
            shutil.copyfile(source, Path(staging_dir) / source.name)

            command = [
                str(self.executable_path),
                staging_dir,
                str(output),
                output_version,
                "DXF",
                "0",  # recurse into subfolders: no
                "1",  # audit each file while converting
            ]
            try:
                subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    timeout=self.timeout,
                )
            except subprocess.CalledProcessError as error:
                stderr = error.stderr.decode(errors="replace") if error.stderr else ""
                raise DWGConversionError(
                    f"ODA File Converter failed converting {source.name}: {stderr}"
                ) from error
            except subprocess.TimeoutExpired as error:
                raise DWGConversionError(
                    f"ODA File Converter timed out converting {source.name}"
                ) from error

        produced = output / f"{source.stem}.dxf"
        if not produced.is_file():
            raise DWGConversionError(
                f"ODA File Converter did not produce the expected output: {produced}"
            )
        return produced

    @classmethod
    def _resolve_executable(cls, executable_path: str | Path | None) -> Path | None:
        if executable_path is not None:
            resolved = Path(executable_path)
            return resolved if resolved.is_file() else None

        env_path = os.environ.get("ODA_FILE_CONVERTER_PATH")
        if env_path:
            resolved = Path(env_path)
            if resolved.is_file():
                return resolved

        for name in cls._DEFAULT_EXECUTABLE_NAMES:
            found = shutil.which(name)
            if found:
                return Path(found)
        return None
