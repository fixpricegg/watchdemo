
import json
from pathlib import Path

import numpy as np


INDEX_TYPES = {
    5121: np.dtype("u1"),
    5123: np.dtype("<u2"),
    5125: np.dtype("<u4"),
}


def _local_matrix(node):
    if "matrix" in node:
        if any(
            key in node
            for key in ("translation", "rotation", "scale")
        ):
            raise ValueError("Matrix and TRS cannot be combined")

        values = np.asarray(node["matrix"], dtype=np.float64)

        if values.shape != (16,) or not np.isfinite(values).all():
            raise ValueError("Invalid node matrix")

        matrix = values.reshape((4, 4), order="F")

        if not np.allclose(matrix[3], [0, 0, 0, 1]):
            raise ValueError("Non-affine node matrix")

        return matrix

    translation = np.asarray(
        node.get("translation", [0, 0, 0]), dtype=np.float64
    )
    scale = np.asarray(
        node.get("scale", [1, 1, 1]), dtype=np.float64
    )
    quaternion = np.asarray(
        node.get("rotation", [0, 0, 0, 1]), dtype=np.float64
    )

    if (
        translation.shape != (3,)
        or scale.shape != (3,)
        or quaternion.shape != (4,)
        or not np.isfinite(translation).all()
        or not np.isfinite(scale).all()
        or not np.isfinite(quaternion).all()
    ):
        raise ValueError("Invalid node transform")

    norm = np.linalg.norm(quaternion)

    if norm < 1e-12:
        raise ValueError("Invalid quaternion")

    x, y, z, w = quaternion / norm

    rotation = np.array([
        [
            1 - 2 * (y*y + z*z),
            2 * (x*y - z*w),
            2 * (x*z + y*w),
        ],
        [
            2 * (x*y + z*w),
            1 - 2 * (x*x + z*z),
            2 * (y*z - x*w),
        ],
        [
            2 * (x*z - y*w),
            2 * (y*z + x*w),
            1 - 2 * (x*x + y*y),
        ],
    ])

    matrix = np.eye(4)
    matrix[:3, :3] = rotation @ np.diag(scale)
    matrix[:3, 3] = translation

    return matrix


def _transform_positions(vertices, matrix):
    vertices = np.asarray(vertices, dtype=np.float64)

    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("Invalid vertex positions")

    result = vertices @ matrix[:3, :3].T + matrix[:3, 3]

    if not np.isfinite(result).all():
        raise ValueError("Invalid transformed positions")

    return result


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


def load_physics_mesh(path, *, coordinate_space="gltf"):
    if coordinate_space not in ("gltf", "source2_raw"):
        raise ValueError("Unsupported coordinate space")
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


    nodes = data["nodes"]
    parents = {}

    for parent_index, node in enumerate(nodes):
        for child in node.get("children", []):
            child = int(child)

            if not 0 <= child < len(nodes):
                raise ValueError("Invalid child node")

            if child in parents:
                raise ValueError("Multiple parents for node")

            parents[child] = parent_index

    world_cache = {}
    visiting = set()

    def world_matrix(index):
        if index in world_cache:
            return world_cache[index]

        if index in visiting:
            raise ValueError("Cycle in node hierarchy")

        visiting.add(index)

        try:
            matrix = _local_matrix(nodes[index])
            parent = parents.get(index)

            if parent is not None:
                matrix = world_matrix(parent) @ matrix

            world_cache[index] = matrix
            return matrix
        finally:
            visiting.remove(index)

    groups = []

    for node_index, node in enumerate(nodes):
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

            if coordinate_space == "gltf":
                vertices = _transform_positions(
                    vertices,
                    world_matrix(node_index),
                )

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
