"""Headless Mol* snapshot export for the largest conserved interface patch."""
from __future__ import annotations

import base64
import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


MOLSTAR_VERSION = "5.6.1"


def _npm_root() -> Path | None:
    npm = shutil.which("npm")
    if not npm:
        return None
    try:
        result = subprocess.run(
            [npm, "root", "-g"], capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    root = Path(result.stdout.strip())
    return root if root.is_dir() else None


def _find_browser() -> str | None:
    candidates = [
        os.environ.get("PUPPETEER_EXECUTABLE_PATH"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


def _find_node_assets() -> tuple[Path, Path, Path] | None:
    root = _npm_root()
    if root is None:
        return None
    viewer = root / "molstar" / "build" / "viewer"
    molstar_js = viewer / "molstar.js"
    molstar_css = viewer / "molstar.css"
    puppeteer_candidates = [
        root / "puppeteer-core",
        root / "highcharts-export-server" / "node_modules" / "puppeteer-core",
    ]
    puppeteer = next((path for path in puppeteer_candidates if path.is_dir()), None)
    if not molstar_js.is_file() or not molstar_css.is_file() or puppeteer is None:
        return None
    return molstar_js, molstar_css, puppeteer


def _snapshot_html(pdb_text: str, residues: list[dict], molstar_js: Path, molstar_css: Path) -> str:
    pdb_b64 = base64.b64encode(pdb_text.encode("utf-8")).decode("ascii")
    residue_json = json.dumps([
        {"chain": str(item.get("chain", "")), "resNum": int(item["resNum"])}
        for item in residues
    ])
    css_url = molstar_css.resolve().as_uri()
    js_url = molstar_js.resolve().as_uri()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><link rel="stylesheet" href="{html.escape(css_url)}">
<style>
html,body,#viewer {{ margin:0; width:1600px; height:1000px; overflow:hidden; background:#fff; }}
#viewer {{ position:relative; }}
.msp-plugin, .msp-plugin-content {{ background:#fff !important; }}
#viewer button, #viewer .msp-toast-container, #viewer .msp-viewport-controls,
#viewer .msp-logo, #viewer .msp-animation-viewport-controls {{ display:none !important; }}
</style></head><body><div id="viewer"></div>
<script src="{html.escape(js_url)}"></script><script>
const PDB_TEXT = atob({json.dumps(pdb_b64)});
const RESIDUES = {residue_json};

async function applyBallAndStick(plugin, residues) {{
  const structures = plugin.managers.structure.hierarchy.current.structures;
  if (!structures || !structures.length) return;
  const structureData = structures[0].cell.obj && structures[0].cell.obj.data;
  const SE = window.molstar && window.molstar.lib && window.molstar.lib.structure.StructureElement;
  if (!structureData || !SE) return;
  const residueSet = new Set(residues.map(r => String(r.chain) + ':' + Number(r.resNum)));
  const bundleLoci = [];
  for (const unit of structureData.units) {{
    const elements = unit.elements, model = unit.model;
    const hierarchy = model.atomicHierarchy;
    if (!hierarchy || !hierarchy.residues || !hierarchy.chains || !hierarchy.residueAtomSegments) continue;
    const matching = [];
    for (let i = 0; i < elements.length; i++) {{
      const atom = elements[i];
      const residueIndex = hierarchy.residueAtomSegments.index[atom];
      const chainIndex = hierarchy.chainAtomSegments.index[atom];
      const chain = hierarchy.chains.auth_asym_id.value(chainIndex);
      const resNum = hierarchy.residues.auth_seq_id.value(residueIndex);
      if (residueSet.has(String(chain) + ':' + Number(resNum))) matching.push(i);
    }}
    if (matching.length) {{
      const math = window.molstar.lib.math || {{}};
      const sorted = new Int32Array(matching);
      let indices;
      if (math.SortedArray && math.SortedArray.ofSortedArray) {{
        indices = math.SortedArray.ofSortedArray(sorted);
      }} else if (math.OrderedSet && math.OrderedSet.ofSortedArray) {{
        indices = math.OrderedSet.ofSortedArray(sorted);
      }} else {{
        indices = sorted;
      }}
      bundleLoci.push({{ unit, indices }});
    }}
  }}
  if (bundleLoci.length) {{
    plugin.managers.structure.focus.setFromLoci(SE.Loci(structureData, bundleLoci));
  }}
}}

(async () => {{
  try {{
    const viewer = await window.molstar.Viewer.create('viewer', {{
      layoutIsExpanded:false, layoutShowControls:false, layoutShowRemoteState:false,
      layoutShowSequence:false, layoutShowLog:false, layoutShowLeftPanel:false,
      viewportShowExpand:false, viewportShowControls:false,
      viewportShowSelectionMode:false, viewportShowAnimation:false
    }});
    const yellow = 0xFCF55F;
    viewer.plugin.canvas3d.setProps({{
      renderer: {{ backgroundColor:0xFFFFFF, selectColor:yellow, highlightColor:yellow }},
      marking: {{ selectEdgeColor:yellow, highlightEdgeColor:yellow }}
    }});
    const plugin = viewer.plugin;
    const data = await plugin.builders.data.rawData({{ data:PDB_TEXT }}, {{ state:{{ isGhost:true }} }});
    const trajectory = await plugin.builders.structure.parseTrajectory(data, 'pdb');
    const model = await plugin.builders.structure.createModel(trajectory);
    const structure = await plugin.builders.structure.createStructure(model);
    const polymer = await plugin.builders.structure.tryCreateComponentStatic(structure, 'polymer');
    const ligand = await plugin.builders.structure.tryCreateComponentStatic(structure, 'ligand');
    const water = await plugin.builders.structure.tryCreateComponentStatic(structure, 'water');
    const update = plugin.state.data.build();
    const builder = plugin.builders.structure.representation;
    if (polymer) builder.buildRepresentation(update, polymer, {{ type:'cartoon', typeParams:{{ alpha:0.8 }} }}, {{ tag:'polymer' }});
    if (ligand) builder.buildRepresentation(update, ligand, {{ type:'ball-and-stick', typeParams:{{ alpha:0.8 }} }}, {{ tag:'ligand' }});
    if (water) builder.buildRepresentation(update, water, {{ type:'ball-and-stick', typeParams:{{ alpha:0.6 }} }}, {{ tag:'water' }});
    await update.commit();
    viewer.structureInteractivity({{
      elements: RESIDUES.map(r => ({{ auth_asym_id:String(r.chain), auth_seq_id:Number(r.resNum) }})),
      action:'select', applyGranularity:true
    }});
    await applyBallAndStick(plugin, RESIDUES);
    if (viewer.handleResize) viewer.handleResize();
    // Focus creation queues additional representation work. Wait until it has
    // settled so screenshots never capture Mol*'s progress toast or a partial
    // patch representation.
    await new Promise(resolve => setTimeout(resolve, 5000));
    window.__MOLSTAR_READY = true;
  }} catch (error) {{
    window.__MOLSTAR_ERROR = error && error.stack ? error.stack : String(error);
  }}
}})();
</script></body></html>"""


def render_molstar_snapshot(
    viewer_pdb: str | Path,
    residues: list[dict],
    output_path: str | Path,
) -> tuple[bool, str | None]:
    """Render *viewer_pdb* with the supplied residues highlighted in Mol*."""
    viewer_pdb = Path(viewer_pdb)
    output_path = Path(output_path)
    assets = _find_node_assets()
    browser = _find_browser()
    node = shutil.which("node")
    runner = Path(__file__).resolve().parent / "_runtime" / "molstar_snapshot.js"
    if not viewer_pdb.is_file():
        return False, f"viewer PDB not found: {viewer_pdb}"
    if not residues:
        return False, "no interface-patch residues to highlight"
    if not node or not browser or not runner.is_file() or assets is None:
        return False, (
            f"Mol* {MOLSTAR_VERSION}, Chromium, or the Node renderer is unavailable. "
            f"Install with: npm install -g molstar@{MOLSTAR_VERSION} highcharts-export-server@5.1.0"
        )

    molstar_js, molstar_css, puppeteer = assets
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = _snapshot_html(
        viewer_pdb.read_text(encoding="utf-8", errors="replace"),
        residues,
        molstar_js,
        molstar_css,
    )
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
            handle.write(html_text)
            temp_path = handle.name
        env = os.environ.copy()
        env["PUPPETEER_MODULE"] = str(puppeteer)
        result = subprocess.run(
            [node, str(runner), temp_path, str(output_path.resolve()), browser],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0 or not output_path.is_file():
            error = (result.stderr or result.stdout or "unknown Mol* renderer error")[-2000:]
            return False, error.strip()
        return True, None
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
