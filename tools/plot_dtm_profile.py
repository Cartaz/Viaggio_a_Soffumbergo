#!/usr/bin/env python3
"""Draw a documentary SVG of DTM ground samples; NOT a verified road grade."""
import argparse
from html import escape
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = "ABCVDEF"


def render(document):
    if (document.get("status") != "REAL_DTM_SAMPLED_NOT_SURVEYED_ROAD"
            or document.get("godot_ready") is not False
            or document.get("vertical_datum") != "UNKNOWN_NOT_VERIFIED"):
        raise ValueError("Only unverified-datum real bare-earth DTM profiles are supported")
    sectors = document["sectors"]
    if "".join(s["sector"] for s in sectors) != ORDER:
        raise ValueError("Unexpected sector sequence")
    positions = []
    chainage = 0.
    boundaries = []
    for segment in sectors:
        boundaries.append((segment["sector"], chainage))
        last = 0.
        for point in segment["samples"]:
            local = point["distance_along_sector_m"]
            if local < last or local > segment["length_projected_m"] + .1:
                raise ValueError("Nonmonotonic sample chainage")
            last = local
            elevation = point["dtm_raw_grid_value_m"]
            if elevation is not None and not math.isfinite(elevation):
                raise ValueError("Nonfinite DTM sample")
            positions.append((chainage + local, elevation))
        chainage += segment["length_projected_m"]
    if not positions or all(z is None for _, z in positions):
        raise ValueError("No sample data")
    WIDTH, HEIGHT = 1200, 680
    left, right, top, bottom = 94, 1155, 124, 528
    good = [z for _, z in positions if z is not None]
    min_y = 100 * math.floor(min(good) / 100)
    max_y = 100 * math.ceil(max(good) / 100)
    if min_y == max_y:
        max_y += 100
    def xcoord(m):
        return left + m / chainage * (right - left)
    def ycoord(v):
        return bottom - (v - min_y) / (max_y - min_y) * (bottom - top)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        '<title id="title">Soffumbergo — campionamento DTM regionale lungo il circuito OSM candidato</title>',
        '<desc id="desc">Profilo della superficie del terreno nudo, dato FVG 10 m. Coordinate e svolte del circuito ancora da verificare; datum verticale sconosciuto. Non rappresenta la quota reale del piano stradale.</desc>',
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f8faf9"/>',
        '<g font-family="DejaVu Sans, Arial, sans-serif">',
        '<text x="76" y="48" font-size="27" fill="#193c37" font-weight="bold">Faedis → Valle di Soffumbergo → Faedis</text>',
        '<text x="76" y="80" font-size="16" fill="#47605b">Profilo DTM Protezione Civile FVG · passo 10 m · 2.394 campioni senza lacune</text>',
        f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="#eef3ef" stroke="#c5d2c9"/>'
    ]
    for h in range(int(min_y), int(max_y) + 1, 100):
        y = ycoord(h)
        svg.extend([f'<line x1="{left}" x2="{right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#c9d5cc" stroke-dasharray="4 5"/>',
                    f'<text x="{left-13}" y="{y+5:.2f}" fill="#49635d" font-size="13" text-anchor="end">{h}</text>'])
    for sector, d in boundaries:
        x = xcoord(d)
        svg.extend([f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{top}" y2="{bottom}" stroke="#b4c9bd" stroke-dasharray="5 4"/>',
                    f'<text x="{x+7:.2f}" y="{top+22}" font-size="17" fill="#244e43" font-weight="bold">{escape(sector)}</text>'])
    path, all_paths = [], []
    for distance, value in positions:
        if value is None:
            if path:
                all_paths.append(path)
                path = []
        else:
            path.append(f"{xcoord(distance):.2f},{ycoord(value):.2f}")
    if path:
        all_paths.append(path)
    for seq in all_paths:
        svg.append(f'<polyline points="{" ".join(seq)}" stroke="#267f61" stroke-width="2.2" fill="none" stroke-linejoin="round"/>')
    for km in range(0, math.ceil(chainage / 1000) + 1, 2):
        x = xcoord(km * 1000)
        if x > right:
            break
        svg.extend([f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{bottom}" y2="{bottom+6}" stroke="#547268"/>',
                    f'<text x="{x:.2f}" y="{bottom+26}" font-size="13" fill="#47605b" text-anchor="middle">{km} km</text>'])
    svg.extend([
        '<text x="76" y="600" font-size="16" font-weight="bold" fill="#813d33">ATTENZIONE — non è un profilo della superficie asfaltata</text>',
        '<text x="76" y="624" font-size="13" fill="#5b5951">Quote grezze del terreno nudo; datum verticale non verificato; tracciato OSM e svolte ancora da validare.</text>',
        '<text x="76" y="648" font-size="12" fill="#5b5951">Sorgente: Regione FVG · DTM PCR 067-NO 10 m (rilievo 2006–2010) · © OpenStreetMap contributors, ODbL 1.0.</text>',
        '</g>', '</svg>'])
    return "\n".join(svg) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT/"data/geography/circuito_dtm10_terrain_profile_20261020.json")
    p.add_argument("--output", type=Path, default=ROOT/"reports/terrain_10m_profile.svg")
    args = p.parse_args()
    content = render(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"Review-only DTM SVG written: {args.output}")


if __name__ == "__main__":
    main()
