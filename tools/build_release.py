"""Build only allowlisted public source and an embedded synthetic demo."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tokens.demo import sample_usage,SAMPLE_RATES
from tokens.pricing import estimate_usage

FILES=['README.md','LICENSE','pyproject.toml','tokens/__init__.py','tokens/inventory.py','tokens/agent.py','tokens/attribution.py','tokens/connections.py','tokens/policy.py','tokens/pricing.py','tokens/demo.py','tokens/web/inventory.html','tokens/skills/local-token-inventory/SKILL.md','MANIFEST.in','tools/build_release.py','tools/audit_release.py','.github/workflows/pages.yml','tests/test_product.py','tests/test_local_server.py','tests/test_release.py']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='token-public-build-') as temporary:
        stage=Path(temporary)
        for name in FILES:
            target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        # Build offline using installed backend tools. No private checkout history
        # or arbitrary data directory is available to the packaging backend.
        subprocess.run([sys.executable,'-c',"import setuptools.build_meta as b;b.build_wheel('dist');b.build_sdist('dist')"],cwd=stage,check=True,stdout=subprocess.DEVNULL)
        for path in (stage/'dist').iterdir():shutil.copy2(path,output/path.name)
    with zipfile.ZipFile(output/'local-token-inventory.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:archive.writestr(name,(ROOT/name).read_bytes())
    with zipfile.ZipFile(output/'local-token-inventory-skill.zip','x',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('local-token-inventory/SKILL.md',(ROOT/'tokens/skills/local-token-inventory/SKILL.md').read_bytes())
    static=output/'static-demo';static.mkdir();(static/'downloads').mkdir();
    for artifact in output.iterdir():
        if artifact.is_file():shutil.copy2(artifact,static/'downloads'/artifact.name)
    page=(ROOT/'tokens/web/inventory.html').read_text()
    demo=estimate_usage(sample_usage(),SAMPLE_RATES)
    replacements={'__SCAN_TOKEN__':'synthetic-browser-only','__STATIC_DEMO__':'true','__DEMO_PAYLOAD__':json.dumps(demo).replace('<','\\u003c'),'__RUN_MODE__':'Synthetic demo · invented data','__CONNECT_LABEL__':'Explore synthetic example','__CONNECT_EXPLAIN__':'Invented projects and counters, processed entirely in this browser. No filesystem or local server access.','__CONNECT_STATUS__':'Synthetic data only.'}
    for old,new in replacements.items():page=page.replace(old,new)
    policy="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'"
    page=page.replace('<title>', '<meta http-equiv="Content-Security-Policy" content="'+policy+'"><title>',1)
    page=page.replace('</footer>', ' <a href="packages.html">Python packages and skill</a></footer>')
    (static/'index.html').write_text(page)
    links=''.join('<li><a href="downloads/'+p.name+'">'+p.name+'</a></li>' for p in sorted((static/'downloads').iterdir()))
    (static/'packages.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private installation packages</title><h1>Run privately</h1><p>Download a wheel, source distribution, source ZIP or setup skill. These files contain code and synthetic examples only.</p><ul>'+links+'</ul><p><a href="index.html">Back to synthetic demo</a></p></html>')
    print(output)

if __name__=='__main__':main()
