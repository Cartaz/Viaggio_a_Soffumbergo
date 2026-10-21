"""Deterministic visual placeholder recipes, independent of editor and raw DTM."""
import hashlib
import math
import re


def observation_code(pano, category_code, bearing):
    # Same panorama/class/direction group reuses an identity across route passes.
    bucket = int(math.floor((bearing % 360 + 22.5)/45)) % 8
    key = f'{pano}:{category_code}:{bucket}'
    return f'PH-{category_code}-SV-'+hashlib.sha256(key.encode()).hexdigest()[:10].upper()


def parse_feature(text, default_heading):
    match = re.fullmatch(r'([a-z]+):([LRF])(?:@(\d{1,3}))?', text)
    if not match:
        raise ValueError('Invalid observation feature: '+text)
    category, side, explicit = match.groups()
    heading = float(explicit) if explicit is not None else float(default_heading)
    if not 0 <= heading < 360:
        raise ValueError('Heading outside compass range')
    return category, side, heading, (heading+{'L':-90, 'R':90, 'F':0}[side]) % 360


def primitive(kind, size, center, color):
    return {'kind':kind, 'size_m':[round(float(v), 6) for v in size],
            'center_m':[round(float(v), 6) for v in center], 'color':color}


def recipe(category):
    """Explicit primitive list, no runtime random state and no measured size claim."""
    shape, (w, h, d), color = category['shape'], category['size_m'], category['color']
    p = []
    if shape in {'tree', 'conifer', 'palm', 'woodland'}:
        centers = [(0, 0)] if shape != 'woodland' else [(-4, -4), (4, -3), (0, 0), (-3, 4), (4, 4)]
        diameter = w if shape != 'woodland' else 5
        for x, z in centers:
            p.append(primitive('cylinder', [.35, h*.55, .35], [x, h*.275, z], '79644d'))
            crown = 'cone' if shape == 'conifer' else 'sphere'
            crown_h = h*.6 if shape != 'palm' else 1.6
            p.append(primitive(crown, [diameter, crown_h, diameter], [x, h-crown_h/2, z], color))
    elif shape == 'vineyard':
        for x in [-w*.4, 0, w*.4]:
            p.append(primitive('box', [.45, h, d], [x, h/2, 0], color))
    elif shape in {'fence', 'guardrail'}:
        for x in [-w/2+.1, 0, w/2-.1]:
            p.append(primitive('box', [.12, h, .12], [x, h/2, 0], color))
        for y in ([h*.45, h*.95] if shape == 'fence' else [h*.85]):
            p.append(primitive('box', [w, .12 if shape == 'fence' else .25, d], [0, y, 0], color))
    elif shape in {'pole', 'lamp', 'sign'}:
        p.append(primitive('cylinder', [.12 if shape != 'pole' else w, h, .12], [0, h/2, 0], color))
        if shape == 'lamp':
            p.append(primitive('sphere', [w, .25, d], [0, h, 0], 'e0ce9a'))
        if shape == 'sign':
            p.append(primitive('box', [w, .65, d], [0, h-.3, 0], color))
    elif shape == 'shelter':
        for x in [-w/2+.1, w/2-.1]:
            for z in [-d/2+.1, d/2-.1]:
                p.append(primitive('box', [.15, h, .15], [x, h/2, z], color))
        p.append(primitive('box', [w, .2, d], [0, h, 0], '8a7970'))
    elif shape == 'steps':
        for index in range(5):
            step = h*(index+1)/5
            p.append(primitive('box', [w, step, d/5], [0, step/2, -d/2+d*(index+.5)/5], color))
    elif shape == 'marker':
        # Access is an amber locator, never an invented drivable spur or driveway.
        p.append(primitive('cone', [w, h, d], [0, h/2, 0], color))
    else:
        p.append(primitive('sphere' if shape == 'sphere' else 'box', [w, h, d], [0, h/2, 0], color))
    return p


def validate_object(obj):
    required = ['code', 'category', 'description', 'position_m', 'yaw_deg', 'primitives',
                'source', 'position_status', 'dimensions_status', 'collision_enabled']
    if any(k not in obj for k in required) or not obj['description'].strip():
        raise ValueError('Incomplete reproducible placeholder')
    if not re.fullmatch(r'PH-[A-Z]+-(?:OSM-[WN]\d+|SV-[A-F0-9]{10})', obj['code']):
        raise ValueError('Unstable placeholder identity')
    if obj['collision_enabled'] or not obj['source']:
        raise ValueError('Unverified blockout must remain visual and sourced')
    if not all(math.isfinite(float(v)) for v in obj['position_m']+[obj['yaw_deg']]):
        raise ValueError('Missing or nonfinite placement')
    if obj['dimensions_status'] not in {'design_assumption', 'osm_plan_rectangle_height_assumed'}:
        raise ValueError('Metric inference from imagery is not supported')
    if not obj['primitives']:
        raise ValueError('Empty recipe')
    for p in obj['primitives']:
        if p['kind'] not in {'box', 'sphere', 'cone', 'cylinder'}:
            raise ValueError('Unsupported primitive')
        if not all(math.isfinite(float(v)) for v in p['size_m']+p['center_m']):
            raise ValueError('Nonfinite primitive')
        if min(p['size_m']) <= 0:
            raise ValueError('Nonpositive primitive')
