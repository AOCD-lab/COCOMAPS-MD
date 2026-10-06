"""
Chart generation — server-side PNG export.

• Highcharts charts → via highcharts-export-server (Node.js CLI)
• Violin plots     → via plotly + kaleido (pure Python)
• Interface Patches → matplotlib bipartite graphs + rich terminal tables
"""
import csv
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from cli.constants import (
    INTERACTION_TYPES,
    INTERACTION_COLOR_RULES,
    TRENDS_KEYS,
    find_interaction_color,
    rgb_to_hex,
    get_interaction_color_hex,
    resolve_interaction_type,
    sort_interaction_legend_series,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> list[dict]:
    """Read a CSV file into a list of dicts."""
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _read_json(path: str) -> dict:
    """Read a JSON file."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _export_highcharts_png(
    chart_options: dict,
    output_path: str,
    width: int = 1600,
    scale: int = 2,
    callback_js: str | None = None,
):
    """
    Export a Highcharts chart to PNG using highcharts-export-server.

    Writes the options JSON to a temp file, invokes the CLI, and saves the PNG.
    Callback code is passed inline because export-server disables loading
    callback files unless its separate file-resource permission is enabled.
    """
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False, encoding='utf-8'
    ) as tmp:
        json.dump(chart_options, tmp, ensure_ascii=False)
        tmp_path = tmp.name

    try:
        cmd = [
            'highcharts-export-server',
            '--infile', tmp_path,
            '--outfile', output_path,
            '--type', 'png',
            '--width', str(width),
            '--scale', str(scale),
        ]
        if callback_js:
            # A leading newline after export-server's injected `return` invokes
            # automatic semicolon insertion and turns the callback into an
            # invalid anonymous function statement.
            cmd += ['--callback', callback_js.strip(), '--allowCodeExecution', '1']

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or 'unknown error')[-3000:]
            console.print(f"  [red]Export error:[/red] {err}")
            return False
        return True
    except FileNotFoundError:
        console.print(
            "[red]Error: highcharts-export-server not found.[/red]\n"
            "  Install it with: [bold]npm install -g highcharts-export-server[/bold]"
        )
        return False
    except subprocess.TimeoutExpired:
        console.print("[red]Export timed out.[/red]")
        return False
    finally:
        os.unlink(tmp_path)


def _matches_selected_types(types_string: str, excluded_type_ids: set) -> bool:
    """Check if an interaction type string matches included types (not excluded)."""
    types_lower = types_string.lower()
    for itype in INTERACTION_TYPES:
        if itype['id'] in excluded_type_ids:
            continue
        for kw in itype['keywords']:
            if kw.lower() in types_lower:
                return True
    return False


def _aggregate_interactions(system_dir: str) -> list[dict]:
    """
    Read raw _interactions.csv (per-frame rows) and aggregate into
    per-residue-pair entries with computed consistency.

    Mirrors backend data.py `_get_interactions_from_csv` exactly.

    Returns list of dicts with keys:
        resName1, resNum1, chain1, resName2, resNum2, chain2,
        consistency (float 0-1), types (set of type strings),
        typePersistence (dict type->float)
    """
    interactions_file = Path(system_dir) / '_interactions.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not interactions_file.exists():
        return []

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    rows = _read_csv(str(interactions_file))

    # Group by residue pair
    pair_map = {}
    for row in rows:
        r1 = f"{row.get('resName1','')}{row.get('resNum1','')}_{row.get('chain1','')}"
        r2 = f"{row.get('resName2','')}{row.get('resNum2','')}_{row.get('chain2','')}"
        key = f"{r1}__{r2}"
        frame_num = int(row.get('frame', 0))

        if key not in pair_map:
            pair_map[key] = {
                'resName1': row.get('resName1', ''),
                'resNum1': row.get('resNum1', ''),
                'chain1': row.get('chain1', ''),
                'resName2': row.get('resName2', ''),
                'resNum2': row.get('resNum2', ''),
                'chain2': row.get('chain2', ''),
                'frames': set(),
                'types': set(),
                'typeFrames': {},
            }

        pair_map[key]['frames'].add(frame_num)
        for t in (row.get('types') or '').split(';'):
            t = t.strip()
            if t:
                pair_map[key]['types'].add(t)
                if t not in pair_map[key]['typeFrames']:
                    pair_map[key]['typeFrames'][t] = set()
                pair_map[key]['typeFrames'][t].add(frame_num)

    # Build aggregated list
    result = []
    for key, entry in pair_map.items():
        consistency = len(entry['frames']) / total_frames if total_frames > 0 else 0
        type_persistence = {
            t: len(frames) / total_frames
            for t, frames in entry['typeFrames'].items()
        }
        result.append({
            'resName1': entry['resName1'],
            'resNum1': entry['resNum1'],
            'chain1': entry['chain1'],
            'resName2': entry['resName2'],
            'resNum2': entry['resNum2'],
            'chain2': entry['chain2'],
            'consistency': consistency,
            'types': entry['types'],
            'typePersistence': type_persistence,
            'typeFrames': {
                t: sorted(frames) for t, frames in entry['typeFrames'].items()
            },
        })

    result.sort(key=lambda x: x['consistency'], reverse=True)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Chart builders
# ─────────────────────────────────────────────────────────────────────────────

def _common_chart_style() -> dict:
    """Common Highcharts styling matching the GUI."""
    return {
        'chart': {
            'backgroundColor': '#ffffff',
        },
        'credits': {'enabled': False},
        'title': {
            'style': {
                'fontSize': '24px',
                'fontWeight': '600',
                'color': '#1d1d1f',
            }
        },
    }


def generate_interaction_trends(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    log_scale: bool = False,
    pair_threshold: float = 0.5,
    type_threshold: float = 0.5,
    excluded_types: set | None = None,
) -> bool:
    """Generate conservation-filtered Interaction Trends line chart PNG."""
    interactions_file = Path(system_dir) / '_interactions.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not interactions_file.exists():
        console.print("  [yellow]Warning: _interactions.csv not found, skipping trends chart[/yellow]")
        return False

    if excluded_types is None:
        excluded_types = {'proximal'}

    # Read metadata for frame numbers
    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        return False

    raw_rows = _read_csv(str(interactions_file))
    observed_frames = sorted({int(row.get('frame', 0)) for row in raw_rows})
    frame_numbers = metadata.get('frameNumbers') or observed_frames
    if not frame_numbers:
        frame_numbers = list(range(1, int(metadata.get('totalFrames', 0)) + 1))
    frame_numbers = [int(frame) for frame in frame_numbers]
    frame_index = {frame: index for index, frame in enumerate(frame_numbers)}
    categories = [str(fn) for fn in frame_numbers]

    trends_by_type = {
        interaction_type['id']: [0] * len(frame_numbers)
        for interaction_type in INTERACTION_TYPES
    }
    for interaction in aggregated:
        if interaction['consistency'] < pair_threshold:
            continue
        qualifying_frames = {}
        for raw_type, frames in interaction.get('typeFrames', {}).items():
            resolved = resolve_interaction_type(raw_type)
            if not resolved:
                continue
            persistence = interaction.get('typePersistence', {}).get(raw_type, 0)
            if persistence < type_threshold:
                continue
            qualifying_frames.setdefault(resolved['id'], set()).update(frames)
        for type_id, frames in qualifying_frames.items():
            for frame in frames:
                index = frame_index.get(int(frame))
                if index is not None:
                    trends_by_type[type_id][index] += 1

    series = []
    for itype in INTERACTION_TYPES:
        deselected = itype['id'] in excluded_types
        raw_data = trends_by_type[itype['id']]
        has_nonzero = any(value > 0 for value in raw_data) and not deselected
        data = [None if log_scale and value == 0 else value for value in raw_data]
        color = get_interaction_color_hex(itype['label'])
        if deselected:
            display_name = f'<span style="color:#8e8e93;font-weight:400;text-decoration:line-through">{itype["label"]}</span>'
        elif has_nonzero:
            display_name = f'<span style="font-weight:700">{itype["label"]}</span>'
        else:
            display_name = f'<span style="color:#9ca3af;font-weight:400">{itype["label"]}</span>'
        series.append({
            'name': display_name,
            'canonicalName': itype['label'],
            'data': data if has_nonzero else [],
            'color': 'rgba(156, 163, 175, 0.14)' if deselected else color,
            'lineWidth': 2,
            'marker': {'enabled': has_nonzero, 'radius': 2.5, 'lineWidth': 1, 'lineColor': '#ffffff'},
            'enableMouseTracking': has_nonzero,
            'showInLegend': True,
            '_hasData': has_nonzero,
            '_isDeselected': deselected,
            '_isAnnotation': False,
        })

    series = sort_interaction_legend_series(series)
    selected_type_ids = {
        interaction_type['id'] for interaction_type in INTERACTION_TYPES
        if interaction_type['id'] not in excluded_types
    }
    totals = [
        sum(trends_by_type[type_id][index] for type_id in selected_type_ids)
        for index in range(len(frame_numbers))
    ]
    series.insert(0, {
        'id': 'total-interactions',
        'name': '<span style="font-weight:700">Total interactions</span>',
        'data': [None if log_scale and value == 0 else value for value in totals],
        'color': '#1d1d1f',
        'lineWidth': 3,
        'dashStyle': 'ShortDash',
        'zIndex': 3,
        'marker': {'enabled': False},
        'showInLegend': True,
        '_hasData': not log_scale or any(value > 0 for value in totals),
        '_isDeselected': False,
    })

    x_title = f'Time ({time_unit})' if time_unit else 'Frame'

    chart_options = {
        **_common_chart_style(),
        'chart': {
            'type': 'line',
            'backgroundColor': '#ffffff',
            'height': 650,
            'width': 1600,
        },
        'title': {
            'text': f'{system_name} - Interaction Type Trends Across Frames',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'xAxis': {
            'categories': categories,
            'title': {
                'text': x_title,
                'style': {'fontSize': '16px', 'fontWeight': '700', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '13px', 'fontWeight': '700', 'color': '#1d1d1f'}},
        },
        'yAxis': {
            'type': 'logarithmic' if log_scale else 'linear',
            'title': {
                'text': f'Number of Conserved Residue-Pair Interactions{" - Log Scale" if log_scale else ""}',
                'style': {'fontSize': '16px', 'fontWeight': '700', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '13px', 'fontWeight': '700', 'color': '#1d1d1f'}},
            'min': 0.1 if log_scale else 0,
        },
        'legend': {
            'align': 'right',
            'verticalAlign': 'middle',
            'layout': 'vertical',
            'useHTML': True,
            'itemStyle': {'fontSize': '13px', 'fontWeight': '500', 'color': '#1d1d1f'},
        },
        'plotOptions': {
            'line': {
                'lineWidth': 2,
                'states': {'hover': {'lineWidth': 3}},
                'marker': {'enabled': True, 'radius': 2.5},
            }
        },
        'series': series,
    }

    return _export_highcharts_png(chart_options, output_path)


def generate_area_chart(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    show_stats: bool = False,
    show_bsa: bool = True,
    show_interface_area: bool = True,
) -> bool:
    """Generate Interface Area (BSA) line chart PNG."""
    area_file = Path(system_dir) / '_area.csv'
    if not area_file.exists():
        console.print("  [yellow]Warning: _area.csv not found, skipping area chart[/yellow]")
        return False

    rows = _read_csv(str(area_file))
    if not rows:
        return False

    # Sort by frame number
    rows.sort(key=lambda r: int(r.get('frame', 0)))

    categories = [str(r.get('frame', '')) for r in rows]

    def safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    total_bsa = [safe_float(r.get('totalBSA')) for r in rows]
    polar_bsa = [safe_float(r.get('polarBSA')) for r in rows]
    nonpolar_bsa = [safe_float(r.get('nonPolarBSA')) for r in rows]

    def calc_stats(data):
        if not data:
            return {'mean': 0, 'stdDev': 0, 'lower': 0, 'upper': 0}
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std = math.sqrt(variance)
        return {'mean': mean, 'stdDev': std, 'lower': max(0, mean - std), 'upper': mean + std}

    x_title = f'Time ({time_unit})' if time_unit else 'Frame'

    # Keep at least one measure visible, matching the mutually constrained web toggles.
    if not show_bsa and not show_interface_area:
        show_bsa = True

    components = [
        {'key': 'total', 'label': 'Total', 'data': total_bsa, 'color': '#0072B2', 'symbol': 'circle'},
        {'key': 'polar', 'label': 'Polar', 'data': polar_bsa, 'color': '#B85C00', 'symbol': 'square'},
        {'key': 'nonpolar', 'label': 'Non-Polar', 'data': nonpolar_bsa, 'color': '#8E5AA9', 'symbol': 'triangle'},
    ]
    measures = [
        {'key': 'bsa', 'label': 'BSA', 'enabled': show_bsa, 'scale': 1.0, 'dashStyle': 'Solid'},
        {'key': 'interface-area', 'label': 'Interface Area', 'enabled': show_interface_area, 'scale': 0.5, 'dashStyle': 'Dash'},
    ]

    series = []
    for measure in measures:
        if not measure['enabled']:
            continue
        for component in components:
            data = [value * measure['scale'] for value in component['data']]
            stats = calc_stats(data)
            series_id = f"{component['key']}-{measure['key']}-line"
            name = f"{component['label']} {measure['label']}"
            if show_stats:
                name += f'<br/><span style="font-size:12px;font-weight:400">{stats["mean"]:.2f} ± {stats["stdDev"]:.2f} Å²</span>'
            series.append({
                'id': series_id,
                'name': name,
                'data': data,
                'color': component['color'],
                'dashStyle': measure['dashStyle'],
                'zIndex': 2,
                'marker': {
                    'symbol': component['symbol'],
                    'fillColor': component['color'] if measure['key'] == 'bsa' else '#ffffff',
                    'lineColor': component['color'],
                    'lineWidth': 1.5,
                },
            })
            if show_stats and stats['stdDev'] > 0:
                series.append({
                    'type': 'arearange',
                    'linkedTo': series_id,
                    'data': [[i, stats['lower'], stats['upper']] for i in range(len(data))],
                    'color': component['color'],
                    'fillOpacity': 0.05 if show_bsa and show_interface_area else 0.10,
                    'lineWidth': 0,
                    'enableMouseTracking': False,
                    'showInLegend': False,
                    'zIndex': 0,
                    'marker': {'enabled': False},
                })

    if show_bsa and show_interface_area:
        area_label = 'Buried Surface Area and Interface Area'
    elif show_interface_area:
        area_label = 'Interface Area'
    else:
        area_label = 'Buried Surface Area'

    chart_options = {
        **_common_chart_style(),
        'chart': {
            'type': 'line',
            'backgroundColor': '#ffffff',
            'height': 750,
            'width': 1600,
            'marginTop': 180,
            'marginBottom': 70,
        },
        'title': {
            'text': f'{system_name} - {area_label} Across Frames',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'xAxis': {
            'categories': categories,
            'title': {
                'text': x_title,
                'style': {'fontSize': '16px', 'fontWeight': '700', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '13px', 'fontWeight': '700', 'color': '#1d1d1f'}},
        },
        'yAxis': {
            'title': {
                'text': f'{area_label} (Å²)',
                'style': {'fontSize': '16px', 'fontWeight': '700', 'color': '#1d1d1f'},
            },
            'labels': {'style': {'fontSize': '13px', 'fontWeight': '700', 'color': '#1d1d1f'}},
        },
        'legend': {
            'align': 'center',
            'verticalAlign': 'top',
            'layout': 'horizontal',
            'useHTML': False,
            'width': 720,
            'itemWidth': 240,
            'itemDistance': 0,
            'itemMarginTop': 6,
            'itemMarginBottom': 10,
            'symbolWidth': 32,
            'symbolPadding': 10,
            'title': {
                'text': 'Mean ± Std Dev (Å²)' if show_stats else None,
                'style': {'fontSize': '12px', 'fontWeight': '400', 'color': '#6e6e73'},
            },
            'itemStyle': {'fontSize': '14px', 'fontWeight': '500', 'color': '#1d1d1f'},
        },
        'plotOptions': {
            'line': {
                'lineWidth': 2,
                'marker': {'enabled': True, 'radius': 3, 'lineWidth': 1, 'lineColor': '#ffffff'},
                'states': {'hover': {'lineWidth': 3}},
            }
        },
        'series': series,
    }

    return _export_highcharts_png(chart_options, output_path)


def generate_interaction_heatmap(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    conservation_threshold: float = 0.5,
    excluded_types: set | None = None,
    show_labels: bool = True,
    chain_a: str = 'A',
    chain_b: str = 'B',
) -> bool:
    """Generate Interaction Heatmap PNG."""
    if excluded_types is None:
        excluded_types = {'proximal'}

    # Aggregate raw per-frame data into per-pair entries with consistency
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        console.print("  [yellow]Warning: _interactions.csv not found or empty, skipping heatmap[/yellow]")
        return False

    # Filter by threshold and excluded types
    interactions = []
    for entry in aggregated:
        if entry['consistency'] < conservation_threshold:
            continue
        # Check if any non-excluded type exists
        has_included_type = False
        for t in entry['types']:
            if _matches_selected_types(t, excluded_types):
                has_included_type = True
                break
        if has_included_type:
            interactions.append(entry)

    if not interactions:
        console.print("  [yellow]Warning: No interactions pass filters for heatmap[/yellow]")
        return False

    # Build residue ID sets
    def fmt_res(entry, suffix):
        return f"{entry[f'resName{suffix}']}{entry[f'resNum{suffix}']}_{entry[f'chain{suffix}']}"

    # Build residue ID sets — sort numerically by residue number
    def sort_key(res_id):
        import re
        match = re.search(r'\d+', res_id)
        return int(match.group()) if match else 0

    res1_set = sorted(set(fmt_res(e, '1') for e in interactions), key=sort_key)
    res2_set = sorted(set(fmt_res(e, '2') for e in interactions), key=sort_key)

    # Build heatmap data — value is 0-100 (percentage) for display
    heatmap_data = []
    for entry in interactions:
        r1 = fmt_res(entry, '1')
        r2 = fmt_res(entry, '2')
        c = entry['consistency']
        x = res1_set.index(r1)
        y = res2_set.index(r2)
        heatmap_data.append({
            'x': x,
            'y': y,
            'value': round(c * 100, 2),
        })

    # ── Dynamic label sizing (mirrors FilteredHeatmap.vue) ──
    x_count = len(res1_set)
    y_count = len(res2_set)

    if x_count <= 10:
        x_font, x_rot = '14px', 0
    elif x_count <= 25:
        x_font, x_rot = '12px', -30
    elif x_count <= 50:
        x_font, x_rot = '10px', -45
    elif x_count <= 80:
        x_font, x_rot = '9px', -60
    else:
        x_font, x_rot = '8px', -90

    if y_count <= 15:
        y_font = '14px'
    elif y_count <= 35:
        y_font = '12px'
    elif y_count <= 60:
        y_font = '10px'
    elif y_count <= 100:
        y_font = '9px'
    else:
        y_font = '8px'

    y_font_val = int(y_font.replace('px', ''))
    row_height = max(12, y_font_val + 4)
    chart_height = max(500, y_count * row_height + 250)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': max(1200, x_count * 25 + 400),
        },
        'title': {
            'text': f'{system_name} - Residue-Residue Interaction Heatmap ({len(heatmap_data)} interactions)',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'subtitle': {'text': None},
        'credits': {'enabled': False},
        'xAxis': {
            'categories': res1_set if show_labels else [],
            'title': {
                'text': f'Chain {chain_a} Residues',
                'style': {'fontSize': '18px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {
                'rotation': x_rot,
                'step': 1,
                'overflow': 'allow',
                'style': {
                    'fontSize': x_font,
                    'fontWeight': '700',
                    'color': '#1d1d1f',
                },
            },
            'gridLineWidth': 1,
            'gridLineColor': '#e5e7eb',
            'tickWidth': 1,
            'tickColor': '#d1d5db',
        },
        'yAxis': {
            'categories': res2_set if show_labels else [],
            'title': {
                'text': f'Chain {chain_b} Residues',
                'style': {'fontSize': '18px', 'fontWeight': '600', 'color': '#1d1d1f'},
            },
            'labels': {
                'step': 1,
                'overflow': 'allow',
                'style': {
                    'fontSize': y_font,
                    'fontWeight': '700',
                    'color': '#1d1d1f',
                },
            },
            'reversed': False,
        },
        'colorAxis': {
            'min': 0,
            'max': 100,
            'reversed': False,
            'tickPositions': [0, 25, 50, 75, 100],
            'stops': [
                [0, '#f5f5f7'],
                [0.3, '#90CAF9'],
                [0.5, '#42A5F5'],
                [0.7, '#1E88E5'],
                [1, '#0D47A1'],
            ],
            'labels': {
                'format': '{value}%',
                'style': {
                    'fontSize': '12px',
                    'fontWeight': '500',
                    'color': '#1d1d1f',
                },
            },
        },
        'legend': {
            'align': 'right',
            'layout': 'vertical',
            'verticalAlign': 'middle',
            'symbolHeight': 300,
            'symbolWidth': 20,
            'reversed': False,
            'title': {
                'text': 'Conservation',
                'style': {
                    'fontSize': '14px',
                    'fontWeight': '600',
                    'color': '#1d1d1f',
                },
            },
        },
        'series': [{
            'name': 'Interaction Conservation',
            'data': heatmap_data,
            'turboThreshold': 10000,
            'borderWidth': 1,
            'borderColor': '#93c5fd',
        }],
    }

    return _export_highcharts_png(chart_options, output_path, width=chart_options['chart']['width'])


def generate_conservation_matrix(
    system_dir: str,
    output_path: str,
    system_name: str = 'System',
    time_unit: str | None = None,
    excluded_types: set | None = None,
    pair_threshold: float = 0.5,
    type_threshold: float = 0.5,
    atom_change_mode: str = 'previous',
) -> bool:
    """
    Generate Conservation Matrix chart PNG.

    Mirrors InteractionConservationMatrix.vue: a timeline heatmap where
    X = frame number, Y = pair-type combination rows, and each interaction
    type has its own colored series.
    """
    interactions_file = Path(system_dir) / '_interactions.csv'
    metadata_file = Path(system_dir) / '_metadata.json'

    if not interactions_file.exists():
        console.print("  [yellow]Warning: _interactions.csv not found, skipping conservation matrix[/yellow]")
        return False

    if excluded_types is None:
        excluded_types = {'proximal'}

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    # Aggregate to get per-pair consistency and type persistence
    aggregated = _aggregate_interactions(system_dir)
    if not aggregated:
        console.print("  [yellow]Warning: _interactions.csv empty, skipping conservation matrix[/yellow]")
        return False

    # Read raw per-frame rows to build the timeline
    raw_rows = _read_csv(str(interactions_file))

    # LEVEL 1: Filter pairs by pair conservation threshold
    stable_pairs = [e for e in aggregated if e['consistency'] >= pair_threshold]
    if not stable_pairs:
        console.print("  [yellow]Warning: No pairs pass pair threshold for conservation matrix[/yellow]")
        return False

    # Build pair-type combinations (Y-axis rows)
    def fmt_res(e, s):
        return f"{e[f'resName{s}']}{e[f'resNum{s}']}_{e[f'chain{s}']}"

    def fmt_pair(e):
        return f"{fmt_res(e, '1')} - {fmt_res(e, '2')}"

    # Sort pairs by residue number
    import re
    def pair_sort_key(e):
        num1 = int(re.search(r'\d+', e.get('resNum1', '0')).group()) if re.search(r'\d+', e.get('resNum1', '0')) else 0
        num2 = int(re.search(r'\d+', e.get('resNum2', '0')).group()) if re.search(r'\d+', e.get('resNum2', '0')) else 0
        return (num1, num2)

    stable_pairs.sort(key=pair_sort_key)

    pair_type_combos = []  # list of {'pair': str, 'type': str}
    pair_type_to_row = {}  # "pair__type" -> row index

    for entry in stable_pairs:
        pair_label = fmt_pair(entry)
        # LEVEL 2: filter types by type conservation threshold + excluded
        for t in sorted(entry.get('typePersistence', {}).keys()):
            persistence = entry['typePersistence'][t]
            if persistence < type_threshold:
                continue
            if not _matches_selected_types(t, excluded_types):
                continue
            row_key = f"{pair_label}__{t}"
            if row_key not in pair_type_to_row:
                pair_type_to_row[row_key] = len(pair_type_combos)
                pair_type_combos.append({'pair': pair_label, 'type': t})

    if not pair_type_combos:
        console.print("  [yellow]Warning: No pair-type combinations pass thresholds for conservation matrix[/yellow]")
        return False

    # Keep every interaction type on its own heatmap row, but label each
    # residue pair only once and branch that label to all of its type rows.
    # This mirrors the hierarchy drawn by InteractionConservationMatrix.vue.
    pair_groups = []
    for row_idx, combo in enumerate(pair_type_combos):
        if pair_groups and pair_groups[-1]['pair'] == combo['pair']:
            pair_groups[-1]['rows'].append(row_idx)
        else:
            pair_groups.append({'pair': combo['pair'], 'rows': [row_idx]})

    # Build a lookup: pair_key -> { type -> set of frame numbers }
    pair_type_frames = {}
    for row in raw_rows:
        r1 = f"{row.get('resName1','')}{row.get('resNum1','')}_{row.get('chain1','')}"
        r2 = f"{row.get('resName2','')}{row.get('resNum2','')}_{row.get('chain2','')}"
        pair_label = f"{r1} - {r2}"
        frame_num = int(row.get('frame', 0))
        for t in (row.get('types') or '').split(';'):
            t = t.strip()
            if not t:
                continue
            pt_key = f"{pair_label}__{t}"
            if pt_key in pair_type_to_row:
                if pt_key not in pair_type_frames:
                    pair_type_frames[pt_key] = set()
                pair_type_frames[pt_key].add(frame_num)

    # Build separate heatmap series per interaction type (like GUI)
    series_map = {}  # type -> list of data points
    for pt_key, frames in pair_type_frames.items():
        row_idx = pair_type_to_row.get(pt_key)
        if row_idx is None:
            continue
        itype = pair_type_combos[row_idx]['type']
        if itype not in series_map:
            series_map[itype] = []
        for frame_num in frames:
            series_map[itype].append({
                'x': frame_num,
                'y': row_idx,
                'value': 1,
            })

    # Build series list — each type gets its own colored series
    series = []
    types_with_data = set()
    for itype in sorted(series_map.keys()):
        color = get_interaction_color_hex(itype)
        bold_name = f'<span style="font-weight:700;font-size:12px;color:#1d1d1f">{itype}</span>'
        series.append({
            'type': 'heatmap',
            'name': bold_name,
            'canonicalName': itype,
            'data': series_map[itype],
            'color': color,
            'borderWidth': 1,
            'borderColor': '#e8e8ed',
            'nullColor': 'transparent',
            'colsize': 1,
            'rowsize': 1,
            'dataLabels': {'enabled': False},
            'showInLegend': True,
            '_hasData': True,
            '_isDeselected': False,
            '_isAnnotation': False,
        })
        resolved = resolve_interaction_type(itype)
        if resolved:
            types_with_data.add(resolved['id'])

    # ── Add ALL interaction types to legend (GUI parity) ─────────────
    # Types present in data → bold; absent types → grayed out

    def _type_already_in_series(it_entry):
        """Check canonical identity without confusing polar and apolar contacts."""
        return it_entry['id'] in types_with_data

    for it in INTERACTION_TYPES:
        if _type_already_in_series(it):
            continue
        color = get_interaction_color_hex(it['label'])
        deselected = it['id'] in excluded_types
        if deselected:
            gray_name = f'<span style="color:#8e8e93;font-weight:400;font-size:12px;text-decoration:line-through">{it["label"]}</span>'
        else:
            gray_name = f'<span style="color:#9ca3af;font-weight:400;font-size:12px">{it["label"]}</span>'
        series.append({
            'type': 'heatmap',
            'name': gray_name,
            'canonicalName': it['label'],
            'data': [],
            'color': 'rgba(156, 163, 175, 0.14)' if deselected else color,
            'borderWidth': 1,
            'borderColor': '#e8e8ed',
            'nullColor': 'transparent',
            'colsize': 1,
            'rowsize': 1,
            'dataLabels': {'enabled': False},
            'showInLegend': True,
            '_hasData': False,
            '_isDeselected': deselected,
            '_isAnnotation': False,
        })

    # ── Atom change detection (mirrors GUI hasAtomChange / scatter) ───
    atom_pairs_file = Path(system_dir) / '_atom_pairs.csv'
    if atom_pairs_file.exists():
        ap_rows = _read_csv(str(atom_pairs_file))

        # Build lookup: pair_label -> type -> frame_num -> [atomPair strings]
        ap_lookup = {}  # { "pair_label" : { type : { frame : [atom_pair, ...] } } }
        for r in ap_rows:
            r1 = f"{r.get('resName1','')}{r.get('resNum1','')}_{r.get('chain1','')}"
            r2 = f"{r.get('resName2','')}{r.get('resNum2','')}_{r.get('chain2','')}"
            pair_label = f"{r1} - {r2}"
            itype = r.get('interactionType', '').strip()
            if not itype:
                continue
            frame_num = int(r.get('frame', 0))
            atom1 = r.get('atom1', '')
            atom2 = r.get('atom2', '')
            atom_pair = f"{atom1}-{atom2}"

            ap_lookup.setdefault(pair_label, {}).setdefault(itype, {}).setdefault(frame_num, [])
            if atom_pair not in ap_lookup[pair_label][itype][frame_num]:
                ap_lookup[pair_label][itype][frame_num].append(atom_pair)

        # Sort atom pair lists for consistent comparison
        for pl in ap_lookup.values():
            for tp in pl.values():
                for fr in tp:
                    tp[fr] = sorted(tp[fr])

        def _has_overlap(set1, set2):
            s = set(set1)
            return any(p in s for p in set2)

        def _get_dominant(type_frames_map):
            """Most frequent atom-pair combination across all frames."""
            from collections import Counter
            combo_counts = Counter()
            for frame_num, pairs in type_frames_map.items():
                key = '|'.join(sorted(pairs))
                combo_counts[key] += 1
            if not combo_counts:
                return []
            top_key = combo_counts.most_common(1)[0][0]
            return top_key.split('|') if top_key else []

        def _get_first_frame_pairs(type_frames_map):
            """Atom pairs from the first frame where interaction appears."""
            if not type_frames_map:
                return []
            first_frame = min(type_frames_map.keys())
            return type_frames_map[first_frame]

        atom_change_data = []
        for pt in pair_type_combos:
            pair_label = pt['pair']
            itype = pt['type']
            row_idx = pair_type_to_row.get(f"{pair_label}__{itype}")
            if row_idx is None:
                continue

            type_frames_map = ap_lookup.get(pair_label, {}).get(itype, {})
            if not type_frames_map:
                continue

            # Get frames where this pair-type exists (from pair_type_frames lookup)
            pt_key = f"{pair_label}__{itype}"
            active_frames = sorted(pair_type_frames.get(pt_key, set()))

            for frame_num in active_frames:
                current_pairs = type_frames_map.get(frame_num, [])
                if not current_pairs:
                    continue

                ref_pairs = []
                if atom_change_mode == 'previous':
                    if frame_num <= 1:
                        continue
                    ref_pairs = type_frames_map.get(frame_num - 1, [])
                    if not ref_pairs:
                        continue  # New appearance, not a change
                elif atom_change_mode == 'dominant':
                    ref_pairs = _get_dominant(type_frames_map)
                    if not ref_pairs:
                        continue
                elif atom_change_mode == 'first':
                    ref_pairs = _get_first_frame_pairs(type_frames_map)
                    if not ref_pairs:
                        continue
                    if sorted(current_pairs) == sorted(ref_pairs):
                        continue  # Same as first frame
                else:
                    continue

                # TRUE CHANGE: no overlap between reference and current
                if not _has_overlap(ref_pairs, current_pairs):
                    atom_change_data.append({
                        'x': frame_num,
                        'y': row_idx,
                    })

        if atom_change_data:
            series.append({
                'type': 'scatter',
                'name': 'Atom Changes',
                'color': '#FF9500',
                'data': atom_change_data,
                'marker': {
                    'symbol': 'circle',
                    'radius': 4,
                    'fillColor': '#FF9500',
                    'lineColor': '#FFFFFF',
                    'lineWidth': 1,
                },
                'showInLegend': True,
                'enableMouseTracking': True,
                'zIndex': 10,
                '_hasData': True,
                '_isDeselected': False,
                '_isAnnotation': True,
            })

    series = sort_interaction_legend_series(series)

    unique_pairs = len(pair_groups)
    x_title = f'Time ({time_unit})' if time_unit else 'Frame'
    tick_interval = max(1, total_frames // 20)

    chart_height = max(600, len(pair_type_combos) * 25 + 200)
    chart_width = max(1200, total_frames * 12 + 450)

    chart_options = {
        'chart': {
            'type': 'heatmap',
            'backgroundColor': '#ffffff',
            'height': chart_height,
            'width': chart_width,
            'zoomType': 'xy',
            'marginLeft': 250,
            'marginRight': 200,
        },
        'title': {
            'text': f'{system_name} - Interaction Conservation Timeline ({len(pair_type_combos)} interactions, from {unique_pairs} residue pairs)',
            'style': {'fontSize': '24px', 'fontWeight': '600', 'color': '#1d1d1f'},
        },
        'subtitle': {'text': None},
        'credits': {'enabled': False},
        'colors': None,
        'colorAxis': None,
        'xAxis': {
            'title': {
                'text': x_title,
                'style': {'fontSize': '16px', 'fontWeight': '700', 'color': '#000000'},
            },
            'min': 0.5,
            'max': total_frames + 0.5,
            'tickInterval': tick_interval,
            'labels': {
                'style': {'fontSize': '13px', 'fontWeight': '700', 'color': '#000000'},
            },
            'gridLineWidth': 0,
            'lineWidth': 1,
            'lineColor': '#d2d2d7',
            'tickWidth': 1,
            'tickColor': '#d2d2d7',
            'plotLines': [{'value': i + 0.5, 'color': '#e8e8ed', 'width': 1, 'zIndex': 1} for i in range(total_frames + 1)],
        },
        'yAxis': {
            'title': {'text': ''},
            'min': -0.5,
            'max': len(pair_type_combos) - 0.5,
            'tickPositions': list(range(len(pair_type_combos))),
            'categories': [''] * len(pair_type_combos),
            'labels': {'enabled': False},
            'gridLineWidth': 0,
            'lineWidth': 1,
            'lineColor': '#d2d2d7',
            'tickWidth': 1,
            'tickColor': '#d2d2d7',
            'reversed': False,
            'startOnTick': False,
            'endOnTick': False,
            'plotLines': [{'value': i - 0.5, 'color': '#e8e8ed', 'width': 1, 'zIndex': 1} for i in range(len(pair_type_combos) + 1)],
        },
        'plotOptions': {
            'heatmap': {
                'borderWidth': 1,
                'borderColor': '#e8e8ed',
            },
        },
        'legend': {
            'enabled': True,
            'align': 'right',
            'verticalAlign': 'top',
            'layout': 'vertical',
            'y': 60,
            'useHTML': True,
            'itemStyle': {
                'fontSize': '12px',
                'fontWeight': '500',
                'color': '#1d1d1f',
            },
            'maxHeight': 400,
            'navigation': {
                'activeColor': '#3B6EF5',
                'inactiveColor': '#6e6e73',
            },
        },
        'series': series,
    }

    pair_groups_json = json.dumps(pair_groups, ensure_ascii=False)
    hierarchy_callback = f"""
function (chart) {{
  var pairGroups = {pair_groups_json};
  var yAxis = chart.yAxis && chart.yAxis[0];
  if (!yAxis || !pairGroups.length) return;

  var renderer = chart.renderer;
  var group = renderer.g('pair-hierarchy-labels').attr({{ zIndex: 8 }}).add();
  var plotLeft = chart.plotLeft;
  var labelX = plotLeft - 54;
  var connectorStartX = labelX + 8;
  var bracketX = plotLeft - 34;
  var rowEndX = plotLeft - 8;
  var lineAttrs = {{ stroke: '#8e8e93', 'stroke-width': 1.2, zIndex: 8 }};

  pairGroups.forEach(function (pairGroup) {{
    var rowCenters = pairGroup.rows.map(function (row) {{
      return yAxis.toPixels(row, false);
    }});
    var topY = Math.min.apply(null, rowCenters);
    var bottomY = Math.max.apply(null, rowCenters);
    var centerY = (topY + bottomY) / 2;

    renderer.text(pairGroup.pair, labelX, centerY + 4)
      .attr({{ align: 'right', title: pairGroup.pair, zIndex: 9 }})
      .css({{ color: '#1d1d1f', fontSize: '11px', fontWeight: '600' }})
      .add(group);
    renderer.path([['M', connectorStartX, centerY], ['L', bracketX, centerY]])
      .attr(lineAttrs).add(group);

    if (rowCenters.length > 1) {{
      renderer.path([['M', bracketX, topY], ['L', bracketX, bottomY]])
        .attr(lineAttrs).add(group);
    }}
    rowCenters.forEach(function (rowY) {{
      renderer.path([['M', bracketX, rowY], ['L', rowEndX, rowY]])
        .attr(lineAttrs).add(group);
    }});
  }});
}}
"""

    return _export_highcharts_png(
        chart_options,
        output_path,
        width=chart_width,
        callback_js=hierarchy_callback,
    )


def generate_violin_plots(
    system_dir: str,
    output_dir: str,
    system_name: str = 'System',
    interaction_types: list[str] | None = None,
    min_conservation: int = 50,
    conservation_threshold: float = 0.5,
    type_conservation_threshold: float = 0.5,
    excluded_types: set | None = None,
) -> list[str]:
    """
    Generate violin plot PNGs using Plotly + Kaleido.

    One PNG per interaction type.
    Returns list of generated file paths.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        console.print("[red]plotly not installed. Run: pip install plotly kaleido[/red]")
        return []

    atom_pairs_file = Path(system_dir) / '_atom_pairs.csv'
    metadata_file = Path(system_dir) / '_metadata.json'
    interactions_file = Path(system_dir) / '_interactions.csv'

    if not atom_pairs_file.exists():
        console.print("  [yellow]Warning: _atom_pairs.csv not found, skipping violin plots[/yellow]")
        return []

    metadata = _read_json(str(metadata_file)) if metadata_file.exists() else {}
    total_frames = metadata.get('totalFrames', 1)

    if excluded_types is None:
        excluded_types = {'proximal'}

    # Read atom pairs CSV to discover available interaction types
    ap_rows = _read_csv(str(atom_pairs_file))

    # The column is 'interactionType' (not 'type')
    available_types_set = set()
    for row in ap_rows:
        itype = row.get('interactionType', '').strip()
        if itype and _matches_selected_types(itype, excluded_types):
            available_types_set.add(itype)
    available_types = sorted(available_types_set)

    if interaction_types:
        types_to_plot = [t for t in interaction_types if t in available_types]
    else:
        types_to_plot = available_types

    if not types_to_plot:
        console.print("  [yellow]Warning: No interaction types available for violin plots[/yellow]")
        return []

    aggregated = _aggregate_interactions(system_dir)

    def pair_key_from_parts(res_name1, res_num1, chain1, res_name2, res_num2, chain2):
        return f'{res_name1}{res_num1}_{chain1}__{res_name2}{res_num2}_{chain2}'

    interaction_by_pair = {
        pair_key_from_parts(
            entry['resName1'], entry['resNum1'], entry['chain1'],
            entry['resName2'], entry['resNum2'], entry['chain2'],
        ): entry
        for entry in aggregated
    }

    os.makedirs(output_dir, exist_ok=True)
    generated = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating violin plots", total=len(types_to_plot))

        for itype in types_to_plot:
            progress.update(task, description=f"Violin: {itype}")

            # Filter atom pairs for this interaction type
            # The column name is 'interactionType' (not 'type')
            filtered = [r for r in ap_rows if r.get('interactionType', '').strip() == itype]

            if not filtered:
                progress.update(task, advance=1)
                continue

            # Group by residue pair and retain conservation metadata.
            pair_distances = {}
            for r in filtered:
                lookup_key = pair_key_from_parts(
                    r.get('resName1', ''), r.get('resNum1', ''), r.get('chain1', ''),
                    r.get('resName2', ''), r.get('resNum2', ''), r.get('chain2', ''),
                )
                interaction = interaction_by_pair.get(lookup_key)
                if not interaction:
                    continue
                pair_consistency = interaction.get('consistency', 0)
                type_consistency = interaction.get('typePersistence', {}).get(itype, 0)
                effective_pair_threshold = max(conservation_threshold, min_conservation / 100.0)
                if pair_consistency < effective_pair_threshold or type_consistency < type_conservation_threshold:
                    continue
                pair_label = (
                    f"{r.get('resName1','')}{r.get('resNum1','')}_{r.get('chain1','')} ↔ "
                    f"{r.get('resName2','')}{r.get('resNum2','')}_{r.get('chain2','')}"
                )
                raw_dist = r.get('distance', '').strip()
                if not raw_dist:
                    continue
                try:
                    dist = float(raw_dist)
                except ValueError:
                    continue
                if pair_label not in pair_distances:
                    pair_distances[pair_label] = {
                        'distances': [],
                        'consistency': pair_consistency,
                    }
                pair_distances[pair_label]['distances'].append(dist)

            # Match the web chart: highest-conservation pairs first, then top 50.
            sorted_pairs = sorted(
                pair_distances.items(),
                key=lambda item: (-item[1]['consistency'], item[0]),
            )[:50]

            if not sorted_pairs:
                progress.update(task, advance=1)
                continue

            color = get_interaction_color_hex(itype)
            rgb = find_interaction_color(itype)
            violin_fill = f'rgba({rgb[0]},{rgb[1]},{rgb[2]},0.22)'

            # Build Plotly traces
            traces = []
            pair_labels = []
            local_means = []
            for pair_label, pair_info in sorted_pairs:
                distances = pair_info['distances']
                pair_labels.append(pair_label)
                local_means.append(sum(distances) / len(distances))
                traces.append(go.Violin(
                    y=distances,
                    x=[pair_label] * len(distances),
                    name=pair_label,
                    box_visible=False,
                    meanline_visible=False,
                    fillcolor=violin_fill,
                    opacity=1,
                    line=dict(color=color, width=1.5),
                    points='all',
                    pointpos=0,
                    jitter=0.3,
                    marker=dict(size=4, color=color, opacity=1.0, line=dict(width=0.5, color='#ffffff')),
                    scalemode='width',
                    width=0.9,
                    showlegend=False,
                ))

            # Global mean
            all_dists = [
                distance
                for _, pair_info in sorted_pairs
                for distance in pair_info['distances']
            ]
            global_mean = sum(all_dists) / len(all_dists) if all_dists else 0

            traces.append(go.Scatter(
                x=[None], y=[None], mode='lines',
                line=dict(color='#1d1d1f', width=2.5, dash='dash'),
                name=f'Global Mean: {global_mean:.2f} Å',
                showlegend=True,
                hoverinfo='skip',
            ))
            traces.append(go.Scatter(
                x=pair_labels, y=local_means, mode='markers',
                marker=dict(symbol='line-ew', size=18, color=color, line=dict(width=2.5, color=color)),
                showlegend=False,
                hoverinfo='skip',
            ))

            chart_height = 650

            layout = go.Layout(
                title=dict(
                    text=f'{system_name} - Distance Distribution: {itype}',
                    x=0.5,
                    xanchor='center',
                    yanchor='top',
                    font=dict(size=24, color='#1d1d1f'),
                ),
                shapes=[{
                    'type': 'line',
                    'x0': 0, 'x1': 1,
                    'xref': 'paper',
                    'y0': global_mean, 'y1': global_mean,
                    'yref': 'y',
                    'line': {'color': '#1d1d1f', 'width': 2.5, 'dash': 'dash'},
                    'layer': 'above',
                }],
                xaxis=dict(
                    title=dict(text='Residue Pairs', font=dict(size=15, color='#1d1d1f', weight=700)),
                    tickangle=-45,
                    tickfont=dict(size=12, color='#1d1d1f', weight=700),
                    automargin=True,
                    showline=True,
                    linecolor='#ccd6eb',
                    showgrid=False,
                ),
                yaxis=dict(
                    title=dict(text='Distance (\u00c5)', font=dict(size=15, color='#1d1d1f', weight=700)),
                    tickfont=dict(size=12, color='#1d1d1f', weight=700),
                    automargin=True,
                    gridcolor='#e6e6e6',
                    gridwidth=1,
                    zeroline=False,
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=80, r=24, t=110, b=130),
                height=chart_height,
                hovermode='closest',
                violinmode='group',
                legend=dict(
                    orientation='h', x=0.5, y=1.04,
                    xanchor='center', yanchor='bottom',
                    bgcolor='rgba(0,0,0,0)', borderwidth=0,
                    font=dict(size=14, color='#1d1d1f'),
                ),
                font=dict(size=12, color='#1d1d1f'),
            )

            fig = go.Figure(data=traces, layout=layout)

            safe_name = itype.replace('/', '_').replace(' ', '_').replace('\u03c0', 'pi')
            out_file = os.path.join(output_dir, f'dist_{safe_name}.png')
            try:
                fig.write_image(out_file, width=1400, height=chart_height, scale=2)
                generated.append(out_file)
            except Exception as e:
                console.print(f"  [red]Failed to export {itype}: {e}[/red]")

            progress.update(task, advance=1)

    return generated


def _load_interface_patches(system_dir: str) -> tuple[list[dict], float]:
    """Build the same thresholded interface-patch graph used by the web UI."""
    interface_patches_file = Path(system_dir) / '_interface_patches.json'
    if not interface_patches_file.exists():
        return [], 0.70

    data = _read_json(str(interface_patches_file))
    edges = data.get('edges', []) if isinstance(data, dict) else []
    total_frames = int(data.get('totalFrames', 0)) if isinstance(data, dict) else 0
    threshold = float(data.get('defaultThreshold', 0.70)) if isinstance(data, dict) else 0.70
    minimum_patch_size = max(3, int(data.get('minimumPatchSize', 3))) if isinstance(data, dict) else 3

    adjacency = {}
    residues = {}
    edge_conservation = {}
    for edge in edges:
        source = edge.get('source') or {}
        target = edge.get('target') or {}
        conservation = (
            float(edge.get('frameCount', 0)) / total_frames
            if total_frames > 0
            else float(edge.get('conservation', 0))
        )
        if conservation < threshold:
            continue
        source_key = (source.get('chain'), source.get('resNum'))
        target_key = (target.get('chain'), target.get('resNum'))
        if source_key == target_key:
            continue
        residues[source_key] = source
        residues[target_key] = target
        adjacency.setdefault(source_key, set()).add(target_key)
        adjacency.setdefault(target_key, set()).add(source_key)
        edge_key = tuple(sorted((source_key, target_key), key=lambda node: (str(node[0]), str(node[1]))))
        edge_conservation[edge_key] = conservation

    components = []
    visited = set()
    for start in adjacency:
        if start in visited:
            continue
        stack = [start]
        component = []
        visited.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency.get(node, ()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        if len(component) >= minimum_patch_size:
            components.append(component)

    components.sort(key=lambda component: (
        -len(component),
        str(sorted(component, key=lambda node: (str(node[0]), str(node[1])))),
    ))
    interface_patches = []
    for index, component in enumerate(components, 1):
        component_set = set(component)
        patch_edges = [
            {'source': source, 'target': target, 'conservation': conservation}
            for (source, target), conservation in edge_conservation.items()
            if source in component_set and target in component_set
        ]
        interface_patches.append({
            'id': index,
            'size': len(component),
            'chains': sorted({str(residues[node].get('chain', '')) for node in component}),
            'residues': sorted(
                (residues[node] for node in component),
                key=lambda residue: (str(residue.get('chain', '')), str(residue.get('resNum', ''))),
            ),
            'edges': patch_edges,
        })

    return interface_patches, threshold


def _format_patch_residue(residue: dict) -> str:
    return f"{residue.get('resName', '')}{residue.get('resNum', '')}_{residue.get('chain', '')}"


def generate_interface_patch_charts(
    system_dir: str,
    output_dir: str,
    system_name: str = 'System',
) -> list[str]:
    """Export one web-style bipartite network PNG for each interface patch."""
    interface_patches, threshold = _load_interface_patches(system_dir)
    if not interface_patches:
        return []

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    generated = []
    for patch in interface_patches:
        chains = patch['chains']
        by_chain = {
            chain: sorted(
                (residue for residue in patch['residues'] if str(residue.get('chain', '')) == chain),
                key=lambda residue: (
                    (0, int(residue.get('resNum', 0)))
                    if str(residue.get('resNum', '')).lstrip('-').isdigit()
                    else (1, str(residue.get('resNum', '')))
                ),
            )
            for chain in chains
        }
        max_count = max((len(items) for items in by_chain.values()), default=1)
        figure_height = max(5.0, min(24.0, 1.4 + max_count * 0.34))
        fig, ax = plt.subplots(figsize=(12, figure_height), facecolor='white')

        x_positions = {
            chain: (0.5 if len(chains) == 1 else index / (len(chains) - 1))
            for index, chain in enumerate(chains)
        }
        positions = {}
        for chain in chains:
            items = by_chain[chain]
            for index, residue in enumerate(items):
                y = 0.5 if len(items) == 1 else 1.0 - index / (len(items) - 1)
                key = (residue.get('chain'), residue.get('resNum'))
                positions[key] = (x_positions[chain], y)

        for edge in patch['edges']:
            source = tuple(edge['source'])
            target = tuple(edge['target'])
            if source not in positions or target not in positions:
                continue
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            ax.plot(
                [x1, x2], [y1, y2], color='#c7c7cc',
                linewidth=1.0 + 1.5 * float(edge.get('conservation', 0)),
                alpha=0.75, zorder=1,
            )

        for chain_index, chain in enumerate(chains):
            color = '#007aff' if chain == 'A' else '#ff9500'
            for residue in by_chain[chain]:
                key = (residue.get('chain'), residue.get('resNum'))
                x, y = positions[key]
                ax.scatter([x], [y], s=115, color=color, edgecolor='white', linewidth=1.5, zorder=3)
                alignment = 'right' if chain_index == 0 else 'left'
                offset = -0.025 if chain_index == 0 else 0.025
                ax.text(
                    x + offset, y, _format_patch_residue(residue),
                    ha=alignment, va='center', fontsize=9, fontweight='bold', color='#1d1d1f',
                )

        ax.set_title(
            f"{system_name} - Interface Patch {patch['id']}\n"
            f"{patch['size']} residues | Chains: {', '.join(chains)} | Conservation ≥ {threshold * 100:.0f}%",
            fontsize=16, fontweight='bold', color='#1d1d1f', pad=20,
        )
        ax.set_xlim(-0.24, 1.24)
        ax.set_ylim(-0.04, 1.04)
        ax.axis('off')
        fig.tight_layout()
        output_path = os.path.join(output_dir, f"interface_patch_{patch['id']}.png")
        fig.savefig(output_path, dpi=180, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        generated.append(output_path)

    return generated


def display_interface_patches(system_dir: str, system_name: str = 'System'):
    """Print interface patches as a formatted table to the terminal."""
    interface_patches_file = Path(system_dir) / '_interface_patches.json'
    if not interface_patches_file.exists():
        console.print("  [yellow]Warning: interface patch data not found[/yellow]")
        return

    interface_patches, threshold = _load_interface_patches(system_dir)

    if not interface_patches:
        console.print("  [dim]No interface patches found.[/dim]")
        return

    console.print()
    console.print(Panel(
        f"[bold]{len(interface_patches)} Interface Patch(es)[/bold] ({threshold * 100:.0f}% threshold)",
        title=f"{system_name} — Interface Patches",
        border_style="cyan",
    ))

    for interface_patch in interface_patches:
        table = Table(
            title=f"Interface Patch {interface_patch.get('id', '?')} — {interface_patch.get('size', '?')} residues | Chains: {', '.join(interface_patch.get('chains', []))}",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
        )
        table.add_column("Chain", style="cyan")
        table.add_column("Res #", style="green")
        table.add_column("Res Name")

        for res in interface_patch.get('residues', []):
            table.add_row(
                str(res.get('chain', '')),
                str(res.get('resNum', '')),
                str(res.get('resName', '—')),
            )

        console.print(table)
        console.print()


def generate_interface_patch_3d_snapshot(system_dir: str, output_path: str) -> bool:
    """Render the cleaned first frame with the web-default largest patch(es)."""
    interface_patches, _threshold = _load_interface_patches(system_dir)
    if not interface_patches:
        console.print("  [yellow]Warning: no interface patch available for Mol* snapshot[/yellow]")
        return False

    largest_size = interface_patches[0]['size']
    largest_patches = [patch for patch in interface_patches if patch['size'] == largest_size]
    residues = []
    seen = set()
    for patch in largest_patches:
        for residue in patch['residues']:
            key = (str(residue.get('chain', '')), str(residue.get('resNum', '')))
            if key not in seen:
                seen.add(key)
                residues.append(residue)

    from cli.molstar_snapshot import render_molstar_snapshot
    ok, error = render_molstar_snapshot(
        Path(system_dir) / 'viewer.pdb', residues, output_path,
    )
    if not ok:
        console.print(f"  [yellow]Warning: Mol* snapshot skipped: {error}[/yellow]")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Master chart generation function
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_charts(
    system_dir: str,
    system_name: str,
    global_controls: dict,
    matrix_opts: dict | None,
    heatmap_opts: dict | None,
    trends_opts: dict | None,
    distribution_opts: dict | None,
    area_opts: dict | None,
    show_interface_patches: bool = True,
) -> list[str]:
    """
    Generate all requested charts.

    Returns list of generated file paths.
    """
    charts_dir = os.path.join(system_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    generated = []

    threshold = global_controls.get('conservation_threshold', 0.5)
    time_unit = global_controls.get('time_unit')
    excluded = global_controls.get('excluded_types', {'proximal'})

    console.print()
    console.print(Panel(
        "[bold]Generating charts …[/bold]",
        title="Chart Export",
        border_style="green",
    ))

    chart_total = sum(option is not None for option in (
        matrix_opts, heatmap_opts, trends_opts, area_opts, distribution_opts,
    )) + (2 if show_interface_patches else 0)
    chart_progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )
    chart_progress.start()
    chart_task = chart_progress.add_task("Preparing chart exports", total=chart_total)

    # 1. Conservation Matrix
    if matrix_opts is not None:
        chart_progress.update(chart_task, description="Exporting conservation matrix")
        console.print("\n  [bold]Conservation Matrix[/bold] …")
        out = os.path.join(charts_dir, 'conservation_matrix.png')
        ok = generate_conservation_matrix(
            system_dir, out, system_name,
            time_unit=time_unit,
            excluded_types=excluded,
            pair_threshold=matrix_opts.get('pair_threshold', 0.5),
            type_threshold=matrix_opts.get('type_threshold', 0.5),
            atom_change_mode=matrix_opts.get('atom_change_mode', 'previous'),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")
        chart_progress.update(chart_task, advance=1)

    # 2. Interaction Heatmap
    if heatmap_opts is not None:
        chart_progress.update(chart_task, description="Exporting interaction heatmap")
        console.print("\n  [bold]Interaction Heatmap[/bold] …")
        out = os.path.join(charts_dir, 'interaction_heatmap.png')
        ok = generate_interaction_heatmap(
            system_dir, out, system_name,
            conservation_threshold=threshold,
            excluded_types=excluded,
            show_labels=heatmap_opts.get('show_labels', True),
            chain_a=global_controls.get('chain_a', 'A'),
            chain_b=global_controls.get('chain_b', 'B'),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")
        chart_progress.update(chart_task, advance=1)

    # 3. Interaction Trends
    if trends_opts is not None:
        chart_progress.update(chart_task, description="Exporting interaction trends")
        console.print("\n  [bold]Interaction Trends[/bold] …")
        out = os.path.join(charts_dir, 'interaction_trends.png')
        ok = generate_interaction_trends(
            system_dir, out, system_name,
            time_unit=time_unit,
            log_scale=trends_opts.get('log_scale', False),
            pair_threshold=threshold,
            type_threshold=trends_opts.get('type_threshold', 0.5),
            excluded_types=excluded,
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")
        chart_progress.update(chart_task, advance=1)

    # 4. Interface Area
    if area_opts is not None:
        chart_progress.update(chart_task, description="Exporting interface area")
        console.print("\n  [bold]Interface Area[/bold] …")
        out = os.path.join(charts_dir, 'interface_area.png')
        ok = generate_area_chart(
            system_dir, out, system_name,
            time_unit=time_unit,
            show_stats=area_opts.get('show_stats', False),
            show_bsa=area_opts.get('show_bsa', True),
            show_interface_area=area_opts.get('show_interface_area', True),
        )
        if ok:
            generated.append(out)
            console.print(f"  [green]✓[/green] {out}")
        chart_progress.update(chart_task, advance=1)

    # 5. Distance Distribution (violin plots)
    if distribution_opts is not None:
        chart_progress.update(chart_task, description="Exporting distance distributions")
        console.print("\n  [bold]Distance Distribution[/bold] ...")
        # The violin exporter has genuine per-interaction-type progress. Pause
        # the family-level display so Rich never renders competing live bars.
        chart_progress.stop()
        try:
            files = generate_violin_plots(
                system_dir,
                os.path.join(charts_dir, 'distance_distribution'),
                system_name,
                interaction_types=distribution_opts.get('types'),
                min_conservation=distribution_opts.get('min_conservation', 50),
                conservation_threshold=threshold,
                type_conservation_threshold=distribution_opts.get('type_threshold', threshold),
                excluded_types=excluded,
            )
        finally:
            chart_progress.start()
        chart_progress.update(chart_task, advance=1)
        generated.extend(files)
        if files:
            console.print(f"  [green]\u2713[/green] {len(files)} Distance Distribution chart(s) generated")

    # 6. Interface Patches
    if show_interface_patches:
        chart_progress.update(chart_task, description="Exporting interface patch charts")
        console.print("\n  [bold]Interface Patches[/bold] …")
        files = generate_interface_patch_charts(
            system_dir,
            os.path.join(charts_dir, 'interface_patches'),
            system_name,
        )
        generated.extend(files)
        if files:
            console.print(f"  [green]✓[/green] {len(files)} Interface Patch chart(s) generated")
        chart_progress.update(chart_task, advance=1, description="Rendering Mol* 3D snapshot")
        snapshot_out = os.path.join(charts_dir, 'interface_patch_3d.png')
        console.print("  [dim]Rendering Mol* 3D snapshot (this can take 20–30 seconds) …[/dim]")
        if generate_interface_patch_3d_snapshot(system_dir, snapshot_out):
            generated.append(snapshot_out)
            console.print(f"  [green]✓[/green] {snapshot_out}")
        chart_progress.update(chart_task, advance=1)
        display_interface_patches(system_dir, system_name)

    # Summary
    chart_progress.stop()
    console.print()
    if generated:
        console.print(Panel(
            f"[bold green]{len(generated)} chart(s) saved to:[/bold green] {charts_dir}",
            title="Charts Complete",
            border_style="green",
        ))
    else:
        console.print("[yellow]No charts were generated.[/yellow]")

    return generated
