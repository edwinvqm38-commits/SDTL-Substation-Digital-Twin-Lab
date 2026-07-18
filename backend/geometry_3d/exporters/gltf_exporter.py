from __future__ import annotations

import base64
import json
from math import cos, radians, sin
from pathlib import Path
import struct
from typing import Any

from backend.geometry_3d.models import Object3D, Transform


class GLTFExporter:
    """Export Object3D geometry and SDTL metadata as embedded glTF 2.0 JSON."""

    def prepare(self, object_3d: Object3D) -> dict[str, Any]:
        binary = bytearray()
        buffer_views: list[dict[str, Any]] = []
        accessors: list[dict[str, Any]] = []
        materials: list[dict[str, Any]] = []
        material_indices: dict[str, int] = {}
        meshes: list[dict[str, Any]] = []
        nodes: list[dict[str, Any]] = []
        document_metadata = self._document_metadata(object_3d)

        nodes.append(
            {
                "name": object_3d.id,
                "children": list(range(1, len(object_3d.components) + 1)),
                **self._transform_payload(object_3d.transform),
                "extras": {"metadata": document_metadata},
            }
        )

        for component in object_3d.components:
            material_key = component.material.model_dump_json()
            if material_key not in material_indices:
                material_indices[material_key] = len(materials)
                materials.append(self._material_payload(component.material.model_dump()))
            material_index = material_indices[material_key]

            position_accessor = self._append_accessor(
                binary,
                buffer_views,
                accessors,
                [self._z_up_to_y_up(value) for value in component.mesh.vertices],
                component_type=5126,
                accessor_type="VEC3",
                target=34962,
                include_bounds=True,
            )
            attributes = {"POSITION": position_accessor}
            if component.mesh.normals:
                attributes["NORMAL"] = self._append_accessor(
                    binary,
                    buffer_views,
                    accessors,
                    [self._z_up_to_y_up(value) for value in component.mesh.normals],
                    component_type=5126,
                    accessor_type="VEC3",
                    target=34962,
                )

            indices = self._triangulate(component.mesh.faces)
            index_component_type = 5123 if max(indices, default=0) <= 65535 else 5125
            index_accessor = self._append_accessor(
                binary,
                buffer_views,
                accessors,
                indices,
                component_type=index_component_type,
                accessor_type="SCALAR",
                target=34963,
            )
            component_metadata = {
                **document_metadata,
                "component_id": component.id,
                "component_name": component.name,
                "mesh_id": component.mesh.id,
                "material": component.material.name,
            }
            mesh_index = len(meshes)
            meshes.append(
                {
                    "name": component.mesh.id,
                    "primitives": [
                        {
                            "attributes": attributes,
                            "indices": index_accessor,
                            "mode": 4,
                            "material": material_index,
                        }
                    ],
                    "extras": {
                        **component.mesh.metadata,
                        "metadata": component_metadata,
                    },
                }
            )
            nodes.append(
                {
                    "name": component.name,
                    "mesh": mesh_index,
                    **self._transform_payload(component.transform),
                    "extras": {
                        **component.metadata,
                        "metadata": component_metadata,
                    },
                }
            )

        encoded_buffer = base64.b64encode(binary).decode("ascii")
        return {
            "asset": {"version": "2.0", "generator": "SDTL v1.9.5"},
            "scene": 0,
            "scenes": [{"name": object_3d.id, "nodes": [0]}],
            "nodes": nodes,
            "meshes": meshes,
            "materials": materials,
            "buffers": [
                {
                    "byteLength": len(binary),
                    "uri": f"data:application/octet-stream;base64,{encoded_buffer}",
                }
            ],
            "bufferViews": buffer_views,
            "accessors": accessors,
            "extras": {
                "metadata": document_metadata,
                "source_sdtl_object": object_3d.source_sdtl_object,
                "object_type": object_3d.type,
                "traceability": object_3d.traceability,
                "intermediate_geometry": False,
                "future_target": "Babylon.js",
            },
        }

    def export(self, object_3d: Object3D) -> dict[str, Any]:
        """Compatibility alias for prepare()."""

        return self.prepare(object_3d)

    def to_gltf(self, object_3d: Object3D) -> dict[str, Any]:
        """Return a complete embedded-buffer glTF dictionary."""

        return self.prepare(object_3d)

    def export_json(self, object_3d: Object3D, *, indent: int | None = None) -> str:
        """Serialize the embedded glTF document as JSON."""

        return json.dumps(self.prepare(object_3d), ensure_ascii=True, indent=indent)

    def export_file(self, object_3d: Object3D, path: str | Path) -> Path:
        """Write an embedded-buffer .gltf document and return its path."""

        target = Path(path)
        if target.suffix.lower() != ".gltf":
            raise ValueError("GLTFExporter requires a .gltf output path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.export_json(object_3d, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def _append_accessor(
        binary: bytearray,
        buffer_views: list[dict[str, Any]],
        accessors: list[dict[str, Any]],
        values: list[Any],
        *,
        component_type: int,
        accessor_type: str,
        target: int,
        include_bounds: bool = False,
    ) -> int:
        while len(binary) % 4:
            binary.append(0)
        byte_offset = len(binary)
        flattened = (
            [component for value in values for component in value]
            if accessor_type != "SCALAR"
            else values
        )
        format_code = {5126: "f", 5123: "H", 5125: "I"}[component_type]
        binary.extend(struct.pack(f"<{len(flattened)}{format_code}", *flattened))
        byte_length = len(binary) - byte_offset
        buffer_view_index = len(buffer_views)
        buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": byte_offset,
                "byteLength": byte_length,
                "target": target,
            }
        )
        accessor: dict[str, Any] = {
            "bufferView": buffer_view_index,
            "byteOffset": 0,
            "componentType": component_type,
            "count": len(values),
            "type": accessor_type,
        }
        if include_bounds and values:
            accessor["min"] = [min(value[index] for value in values) for index in range(3)]
            accessor["max"] = [max(value[index] for value in values) for index in range(3)]
        accessors.append(accessor)
        return len(accessors) - 1

    @staticmethod
    def _triangulate(faces: list[list[int]]) -> list[int]:
        triangles: list[int] = []
        for face in faces:
            for index in range(1, len(face) - 1):
                triangles.extend([face[0], face[index], face[index + 1]])
        return triangles

    @staticmethod
    def _document_metadata(object_3d: Object3D) -> dict[str, Any]:
        traceability = object_3d.traceability
        return {
            "sdtl_id": object_3d.source_sdtl_object,
            "source_pdf": traceability.get("source_pdf"),
            "page": traceability.get("page"),
            "source_geometry": traceability.get("source_geometry"),
            "object_type": object_3d.type,
            "state": object_3d.metadata.get("state"),
            "confidence": object_3d.metadata.get("confidence"),
            "dimensions": object_3d.metadata.get("dimensions", {}),
            "material": object_3d.metadata.get("material"),
        }

    @staticmethod
    def _transform_payload(transform: Transform) -> dict[str, list[float]]:
        quaternion = GLTFExporter._euler_to_quaternion(transform.rotation)
        return {
            "translation": GLTFExporter._z_up_to_y_up(transform.position),
            "rotation": GLTFExporter._convert_rotation_to_y_up(quaternion),
            "scale": [transform.scale[0], transform.scale[2], transform.scale[1]],
        }

    @staticmethod
    def _z_up_to_y_up(vector: list[float]) -> list[float]:
        return [vector[0], vector[2], -vector[1]]

    @staticmethod
    def _convert_rotation_to_y_up(quaternion: list[float]) -> list[float]:
        half_sqrt = 2**-0.5
        conversion = [-half_sqrt, 0.0, 0.0, half_sqrt]
        inverse = [half_sqrt, 0.0, 0.0, half_sqrt]
        converted = GLTFExporter._multiply_quaternions(
            GLTFExporter._multiply_quaternions(conversion, quaternion),
            inverse,
        )
        magnitude = sum(value * value for value in converted) ** 0.5
        normalized = [value / magnitude for value in converted]
        return [GLTFExporter._clean_float(value) for value in normalized]

    @staticmethod
    def _clean_float(value: float) -> float:
        if abs(value) < 1e-12:
            return 0.0
        if abs(value - 1.0) < 1e-12:
            return 1.0
        if abs(value + 1.0) < 1e-12:
            return -1.0
        return value

    @staticmethod
    def _multiply_quaternions(left: list[float], right: list[float]) -> list[float]:
        lx, ly, lz, lw = left
        rx, ry, rz, rw = right
        return [
            lw * rx + lx * rw + ly * rz - lz * ry,
            lw * ry - lx * rz + ly * rw + lz * rx,
            lw * rz + lx * ry - ly * rx + lz * rw,
            lw * rw - lx * rx - ly * ry - lz * rz,
        ]

    @staticmethod
    def _euler_to_quaternion(rotation: list[float]) -> list[float]:
        x, y, z = (radians(value) / 2 for value in rotation)
        cx, sx = cos(x), sin(x)
        cy, sy = cos(y), sin(y)
        cz, sz = cos(z), sin(z)
        return [
            sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz,
        ]

    @staticmethod
    def _material_payload(material: dict[str, Any]) -> dict[str, Any]:
        visual = material["visual"]
        color = GLTFExporter._hex_to_rgba(visual["color"], visual.get("opacity", 1.0))
        return {
            "name": material["name"],
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": 0.0,
                "roughnessFactor": 1.0,
            },
            "alphaMode": "BLEND" if color[3] < 1.0 else "OPAQUE",
            "extras": {
                "density": material.get("density"),
                "metadata": material.get("metadata", {}),
            },
        }

    @staticmethod
    def _hex_to_rgba(color: str, opacity: float) -> list[float]:
        value = color.lstrip("#")
        if len(value) != 6:
            raise ValueError(f"Material color must use #RRGGBB format: {color}")
        try:
            channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
        except ValueError as error:
            raise ValueError(f"Invalid material color: {color}") from error
        return [*channels, opacity]
