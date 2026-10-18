#!/usr/bin/env python3
"""Generate a source-linked building inventory and 2D survey map from cached OSM.

Planar preview only: all point heights set to zero solely for the drawing, never
exported as a terrain or driving surface. No Google pixels/geometry are copied.
"""
import csv
from html import escape
import json
from pathlib import Path
from coffa.geography import to_godot

ROOT = Path(__file__).resolve().parents[1]
BBOX = (13.3900, 46.1550, 13.3960, 46.1590)


def main():
    data = json.loads((ROOT / "data/geography/osm_survey.geojson").read_text())
    points = json.loads((ROOT / "data/geography/survey_points.geojson").read_text())
    buildings = [f for f in data["features"] if "building" in f["properties"]]
    roads = [f for f in data["features"] if "highway" in f["properties"]]
    with (ROOT / "reports/valle_building_inventory.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["asset_id", "osm_id", "mapped_name", "source_url", "geometry_status", "height_status", "facade_status", "model_status"])
        for i, f in enumerate(sorted(buildings, key=lambda f: f["properties"]["osm_id"]), 1):
            p = f["properties"]
            writer.writerow([f"VAL-B{i:03d}", p["osm_id"], p.get("name", ""),
                             f"https://www.openstreetmap.org/way/{p['osm_id']}",
                             "mapped_unverified", "unverified", "not_matched_to_photo", "not_modeled"])

    origin = [(BBOX[0] + BBOX[2]) / 2, (BBOX[1] + BBOX[3]) / 2, 0]
    def local(c):
        x, _, z = to_godot([c[0], c[1], 0], origin)
        return x, z
    lower = local([BBOX[0], BBOX[1]])
    upper = local([BBOX[2], BBOX[3]])
    scale = min(820 / (upper[0] - lower[0]), 570 / (lower[1] - upper[1]))
    def screen(c):
        x, z = local(c)
        return 90 + (x - lower[0]) * scale, 140 + (z - upper[1]) * scale
    def path(coords):
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in map(screen, coords))
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="860" viewBox="0 0 1100 860" role="img" aria-labelledby="title desc">',
           '<title id="title">Valle di Soffumbergo — base del sopralluogo</title>',
           '<desc id="desc">Sagome e strade OpenStreetMap, senza quote. La mappa non certifica il percorso a piedi dal prato.</desc>',
           '<rect width="1100" height="860" fill="#f4f1e8"/>',
           '<g font-family="sans-serif" fill="#243e3e">',
           '<text x="55" y="55" font-size="29" font-weight="700">Valle di Soffumbergo</text>',
           f'<text x="55" y="85" font-size="16">Base del sopralluogo · {len(buildings)} sagome mappate · quote assenti · facciate da verificare</text>',
           '<defs><clipPath id="map"><rect x="70" y="120" width="900" height="600"/></clipPath></defs>',
           '<rect x="70" y="120" width="900" height="600" rx="8" fill="#dce5cf"/>',
           '<g clip-path="url(#map)">']
    for f in buildings:
        geom = f["geometry"]
        if geom["type"] != "Polygon":
            continue
        colour = "#b77c53" if f["properties"].get("name", "").startswith("Chiesa") else "#b7aaa0"
        name = f["properties"].get("name", "Edificio OSM " + str(f["properties"]["osm_id"]))
        svg.append(f'<polygon points="{path(geom["coordinates"][0])}" fill="{colour}" stroke="#746b61" stroke-width="0.8"><title>{escape(name)}</title></polygon>')
    for f in roads:
        p = f["properties"]
        minor = p["highway"] in ("path", "footway", "steps", "track")
        dash = 'stroke-dasharray="5 4"' if minor else ''
        svg.append(f'<polyline points="{path(f["geometry"]["coordinates"])}" fill="none" stroke="{("#8b8e6b" if minor else "#fbf6e5")}" stroke-width="{2 if minor else 5}" {dash}><title>{escape(p.get("name", p["highway"]))}</title></polyline>')
    for f in points["features"]:
        x, y = screen(f["geometry"]["coordinates"])
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#a6453b" stroke="#fff" stroke-width="2"/>')
        svg.append(f'<text x="{x+12:.1f}" y="{y-10:.1f}" font-size="14" font-weight="700">{escape(f["id"])}</text>')
    svg.extend(['</g>', '<text x="1000" y="155" font-size="25">N ↑</text>',
                '<text x="55" y="755" font-size="15">PV-01: punto Street View vicino al prato candidato; confini e accesso da confermare.</text>',
                '<text x="55" y="780" font-size="15">SV-CH-01: osservazione davanti alla chiesa. Tratteggi: sentieri, piste o gradini mappati.</text>',
                '<text x="55" y="815" font-size="13">© OpenStreetMap contributors · ODbL 1.0 · openstreetmap.org/copyright</text>',
                '<text x="55" y="836" font-size="13">Disegno planimetrico da dati OSM; nessuna immagine Google incorporata. Copertura parziale.</text>', '</g></svg>'])
    (ROOT / "reports/valle_survey_map.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"Inventory: {len(buildings)} mapped buildings; map generated without elevations.")


if __name__ == "__main__":
    main()
