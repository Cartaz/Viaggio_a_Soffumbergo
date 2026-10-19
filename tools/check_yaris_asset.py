"""Check exported game geometry and articulation contracts using Python stdlib.

These checks detect broken exports, not resemblance to the real car.
"""
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "art/vehicles/yaris_2022"


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    assert magic == b"glTF" and version == 2 and length == len(data), path
    size, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20 + size])
    offset = 20 + size
    size, kind = struct.unpack_from("<II", data, offset)
    assert kind == 0x004E4942
    return doc, data[offset + 8:offset + 8 + size]


def values(doc, buffer, index):
    acc = doc["accessors"][index]
    view = doc["bufferViews"][acc["bufferView"]]
    types = {5126: ("f", 4), 5125: ("I", 4), 5123: ("H", 2), 5121: ("B", 1)}
    fmt, width = types[acc["componentType"]]
    count = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    stride = view.get("byteStride", width * count)
    offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    for i in range(acc["count"]):
        yield struct.unpack_from("<" + fmt * count, buffer, offset + stride * i)


def check_file(path):
    doc, buffer = read_glb(path)
    assert not any(b.get("uri") for b in doc["buffers"]), "External buffer dependency"
    assert all("bufferView" in image for image in doc["images"]), "External texture dependency"
    nodes = {node["name"]: node for node in doc["nodes"]}
    for wheel_id in ("FL", "FR", "RL", "RR"):
        for prefix in ("Wheel_", "Steer_", "Door_"):
            assert prefix + wheel_id in nodes
    fl = nodes["Steer_FL"]["translation"]
    rl = nodes["Steer_RL"]["translation"]
    assert abs(fl[1] - .31045) < 1e-6
    assert abs(abs(fl[2] - rl[2]) - 2.56) < 1e-6
    assert abs(abs(fl[0]) * 2 - 1.518) < 1e-6
    assert abs(abs(rl[0]) * 2 - 1.514) < 1e-6
    assert fl[2] < rl[2], "Forward must be -Z in glTF"
    assert {"Hatch", "SteeringWheel", "DriverEye", "MastRoof"}.issubset(nodes)
    triangles = 0
    vertices = 0
    for mesh in doc["meshes"]:
        for primitive in mesh["primitives"]:
            assert primitive.get("mode", 4) == 4
            attrs = primitive["attributes"]
            assert {"POSITION", "NORMAL", "TEXCOORD_0"}.issubset(attrs)
            positions = list(values(doc, buffer, attrs["POSITION"]))
            assert all(math.isfinite(x) for p in positions for x in p)
            indices = [v[0] for v in values(doc, buffer, primitive["indices"])]
            assert len(indices) % 3 == 0 and max(indices) < len(positions)
            vertices += len(positions)
            triangles += len(indices) // 3
    assert len(doc.get("animations", [])) >= 5, "Missing door/hatch inspection clips"
    return {"file": path.name, "bytes": path.stat().st_size, "triangles": triangles,
            "vertices": vertices, "meshes": len(doc["meshes"]), "materials": len(doc["materials"]),
            "animations": len(doc["animations"])}


def main():
    names = ["yaris_trend_2022.glb", "yaris_trend_2022_lod1.glb", "yaris_trend_2022_lod2.glb",
             "yaris_trend_2022_game.glb"]
    stats = [check_file(ASSET / name) for name in names]
    assert stats[0]["triangles"] > stats[1]["triangles"] > stats[2]["triangles"]
    report = {"export_checks": "passed", "artistic_fidelity": "requires_human_review",
              "files": stats}
    (ROOT / "reports/yaris_2022/export_checks.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
