
import json
from pathlib import Path

import numpy as np


INDEX_TYPES = {
    5121: np.dtype("u1"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
}


def read_accessor(data, buffers, accessor_id):
    accessor = data["accessors"][accessor_id]

    if "sparse" in accessor:
        raise ValueError("Sparse accessors are not supported")

    view = data["bufferViews"][accessor["bufferView"]]

    component_type = accessor["componentType"]
    kind = accessor["type"]
    count = int(accessor["count"])

    if kind == "VEC3" and component_type == 5126:
        dtype = np.dtype("<f4")
        components = 3

    elif kind == "SCALAR" and component_type in INDEX_TYPES:
        dtype = INDEX_TYPES[component_type]
        components = 1

    else:
        raise ValueError(
            f"Unsupported accessor: {kind}, {component_type}"
        )

    buffer = buffers[view["buffer"]]

    offset = (
        int(view.get("byteOffset", 0))
        + int(accessor.get("byteOffset", 0))
    )

    item_size = dtype.itemsize * components
    stride = int(view.get("byteStride", item_size))

    if stride < item_size:
        raise ValueError("Invalid accessor stride")

    if count == 0:
        return np.empty((0, components), dtype=dtype)

    last_byte = offset + (count - 1) * stride + item_size

    if last_byte > len(buffer):
        raise ValueError("Accessor exceeds buffer size")

    result = np.ndarray(
        shape=(count, components),
        dtype=dtype,
        buffer=buffer,
        offset=offset,
        strides=(stride, dtype.itemsize),
    )

    return result.copy()


def load_physics_mesh(path):
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    buffers = []

    for buffer_info in data["buffers"]:
        uri = buffer_info.get("uri")

        if not uri or uri.startswith("data:"):
            raise ValueError("External .bin buffer required")

        buffer_path = (path.parent / uri).resolve()

        if buffer_path.parent != path.parent.resolve():
            raise ValueError("Buffer path outside export folder")

        buffers.append(buffer_path.read_bytes())

    groups = []

    for node in data["nodes"]:
        mesh_id = node.get("mesh")

        if mesh_id is None:
            continue

        mesh = data["meshes"][mesh_id]
        triangles = []

        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                raise ValueError("Non-triangle primitive")

            position_id = primitive["attributes"]["POSITION"]

            vertices = read_accessor(
                data, buffers, position_id
            ).astype(np.float64)

            if "indices" in primitive:
                indices = read_accessor(
                    data, buffers, primitive["indices"]
                ).reshape(-1)

            else:
                indices = np.arange(len(vertices))

            if len(indices) % 3 != 0:
                raise ValueError("Invalid triangle index count")

            if len(indices) and np.max(indices) >= len(vertices):
                raise ValueError("Triangle index out of range")

            triangles.append(
                vertices[indices].reshape(-1, 3, 3)
            )

        if triangles:
            geometry = np.concatenate(triangles)
        else:
            geometry = np.empty((0, 3, 3))

        if not np.isfinite(geometry).all():
            raise ValueError("Non-finite geometry")

        groups.append({
            "name": node.get("name"),
            "surface_property": node.get(
                "extras", {}
            ).get("SurfaceProperty"),
            "interact_as": list(
                node.get("extras", {}).get("InteractAs") or []
            ),
            "node_matrix": node.get("matrix"),
            "triangles_local": geometry,
        })

    return groups
