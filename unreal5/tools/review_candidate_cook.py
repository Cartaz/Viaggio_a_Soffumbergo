"""Record an offline material-compile review of an already completed export."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Preserve the earlier review; select a fresh output')
    draft = args.draft.resolve()
    report_path = draft / 'candidate_packaging_report.json'
    pack = json.loads(report_path.read_text(encoding='utf-8'))
    log_path = Path(pack['uat_log'])
    binary = Path(pack['archive']) / 'Windows/SoffumbergoLab/Binaries/Win64/SoffumbergoLab.exe'
    log = log_path.read_text(encoding='utf-8', errors='replace')
    patterns = [r'failed to compile material', r'default material will be used',
                r'failed to compile global shader', r'shadercompileworker.*crash',
                r'error:\s*shader']
    findings = [{'line': number, 'text': line[:1500]}
                for number, line in enumerate(log.splitlines(), 1)
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)]
    checks = {
        'completed_export': pack.get('packaged') is True and pack.get('exit_code') == 0,
        'binary_matches_export': binary.exists() and sha(binary) == pack.get('game_binary_sha256'),
        'world_matches_export': sha(draft / 'circuit_driving_world.json') == pack['world_sha256'],
        'nullrhi_cook_requested': pack.get('cook_rendering_disabled') is True
            and '-AdditionalCookerOptions=-nullrhi' in pack.get('command', []),
        'no_known_shader_failures_or_material_fallbacks': not findings,
    }
    review = {
        'build_id': pack['build_id'], 'runtime_revision': pack.get('runtime_revision'),
        'attempt': pack['attempt'], 'recorded_unix': time.time(),
        'packaging_report': str(report_path), 'packaging_report_sha256': sha(report_path),
        'uat_log': str(log_path), 'uat_log_sha256': sha(log_path),
        'game_binary_sha256': pack.get('game_binary_sha256'),
        'checks': checks, 'findings': findings, 'passed': all(checks.values()),
        'scope': 'Offline export-log review for explicit known compile failures and material fallbacks. '
                 'No pixels, artistic quality, complete shader correctness or GPU stability acceptance.',
    }
    args.output.write_text(json.dumps(review, indent=2), encoding='utf-8')
    print(json.dumps(review, indent=2))
    if not review['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
