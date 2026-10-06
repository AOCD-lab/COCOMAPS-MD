import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cli import charts
from cli.constants import resolve_interaction_type, sort_interaction_legend_series
from cli.runner import _naccess_succeeded


class ChartParityTests(unittest.TestCase):
    def write_system(self, root: Path):
        (root / '_metadata.json').write_text(
            json.dumps({'totalFrames': 2}), encoding='utf-8'
        )
        with (root / '_interactions.csv').open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                'resName1', 'resNum1', 'chain1', 'resName2', 'resNum2',
                'chain2', 'frame', 'types',
            ])
            writer.writeheader()
            writer.writerow({
                'resName1': 'ALA', 'resNum1': '1', 'chain1': 'A',
                'resName2': 'GLY', 'resNum2': '2', 'chain2': 'B',
                'frame': '1', 'types': 'H-bonds;Proximal contacts',
            })
            writer.writerow({
                'resName1': 'ALA', 'resNum1': '1', 'chain1': 'A',
                'resName2': 'GLY', 'resNum2': '2', 'chain2': 'B',
                'frame': '2', 'types': 'H-bonds;Proximal contacts',
            })

    def test_longest_alias_resolution_keeps_apolar_distinct(self):
        self.assertEqual(resolve_interaction_type('Apolar vdW contacts')['id'], 'apolar-vdw')
        self.assertEqual(resolve_interaction_type('Polar vdW contacts')['id'], 'polar-vdw')

    def test_highcharts_callback_is_passed_inline(self):
        callback = 'function (chart) { chart.renderer.text("ok", 1, 1); }'
        with tempfile.TemporaryDirectory() as temp, patch.object(
            charts.subprocess, 'run', return_value=type('Result', (), {
                'returncode': 0, 'stderr': '', 'stdout': '',
            })(),
        ) as run:
            self.assertTrue(charts._export_highcharts_png(
                {'series': []}, str(Path(temp) / 'chart.png'),
                callback_js=callback,
            ))

        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--callback') + 1], callback)

    def test_trends_are_thresholded_and_include_total(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_system(root)
            captured = {}
            with patch.object(
                charts,
                '_export_highcharts_png',
                side_effect=lambda options, *_args, **_kwargs: captured.update(options=options) or True,
            ):
                self.assertTrue(charts.generate_interaction_trends(
                    str(root), str(root / 'trends.png'), excluded_types={'proximal'},
                    pair_threshold=1.0, type_threshold=1.0,
                ))

            series = captured['options']['series']
            self.assertEqual(series[0]['id'], 'total-interactions')
            self.assertEqual(series[0]['data'], [1, 1])
            self.assertEqual(series[-1]['canonicalName'], 'Proximal contacts')
            self.assertTrue(series[-1]['_isDeselected'])
            self.assertIn(
                'Conserved Residue-Pair',
                captured['options']['yAxis']['title']['text'],
            )

    def test_area_chart_supports_both_measures(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (root / '_area.csv').open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=['frame', 'totalBSA', 'polarBSA', 'nonPolarBSA'],
                )
                writer.writeheader()
                writer.writerow({'frame': 1, 'totalBSA': 100, 'polarBSA': 40, 'nonPolarBSA': 60})
                writer.writerow({'frame': 2, 'totalBSA': 120, 'polarBSA': 50, 'nonPolarBSA': 70})

            captured = {}
            with patch.object(
                charts,
                '_export_highcharts_png',
                side_effect=lambda options, *_args, **_kwargs: captured.update(options=options) or True,
            ):
                self.assertTrue(charts.generate_area_chart(
                    str(root), str(root / 'area.png'), show_stats=False,
                ))

            line_series = [item for item in captured['options']['series'] if item.get('type') != 'arearange']
            self.assertEqual(len(line_series), 6)
            self.assertEqual(line_series[0]['name'], 'Total BSA')
            self.assertEqual(line_series[3]['name'], 'Total Interface Area')
            self.assertEqual(line_series[3]['data'], [50.0, 60.0])
            self.assertEqual(line_series[3]['marker']['fillColor'], '#ffffff')
            self.assertIn(
                'Buried Surface Area and Interface Area Across Frames',
                captured['options']['title']['text'],
            )

    def test_legend_order_places_annotation_before_empty_and_deselected(self):
        ordered = sort_interaction_legend_series([
            {'name': 'Proximal contacts', '_hasData': False, '_isDeselected': True},
            {'name': 'No data', '_hasData': False},
            {'name': 'Atom Changes', '_hasData': True, '_isAnnotation': True},
            {'name': 'H-bonds', '_hasData': True},
        ])
        self.assertEqual([item['name'] for item in ordered], [
            'H-bonds', 'Atom Changes', 'No data', 'Proximal contacts',
        ])

    def test_conservation_matrix_groups_pair_label_across_type_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_system(root)
            captured = {}
            with patch.object(
                charts,
                '_export_highcharts_png',
                side_effect=lambda options, *_args, **kwargs: captured.update(
                    options=options, callback=kwargs.get('callback_js'),
                ) or True,
            ):
                self.assertTrue(charts.generate_conservation_matrix(
                    str(root), str(root / 'matrix.png'), excluded_types=set(),
                    pair_threshold=1.0, type_threshold=1.0,
                ))

            self.assertEqual(len(captured['options']['yAxis']['categories']), 2)
            self.assertEqual(captured['options']['yAxis']['categories'], ['', ''])
            self.assertFalse(captured['options']['yAxis']['labels']['enabled'])
            self.assertEqual(captured['callback'].count("'pair': '"), 0)
            self.assertIn('ALA1_A - GLY2_B', captured['callback'])
            self.assertIn('"rows": [0, 1]', captured['callback'])
            self.assertIn("renderer.path", captured['callback'])

    def test_heatmap_orders_both_axes_ascending(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_system(root)
            with (root / '_interactions.csv').open('a', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    'resName1', 'resNum1', 'chain1', 'resName2', 'resNum2',
                    'chain2', 'frame', 'types',
                ])
                writer.writerow({
                    'resName1': 'ARG', 'resNum1': '10', 'chain1': 'A',
                    'resName2': 'SER', 'resNum2': '20', 'chain2': 'B',
                    'frame': '1', 'types': 'H-bonds',
                })

            captured = {}
            with patch.object(
                charts,
                '_export_highcharts_png',
                side_effect=lambda options, *_args, **_kwargs: captured.update(options=options) or True,
            ):
                self.assertTrue(charts.generate_interaction_heatmap(
                    str(root), str(root / 'heatmap.png'), conservation_threshold=0.5,
                ))

            self.assertEqual(captured['options']['xAxis']['categories'], [
                'ALA1_A', 'ARG10_A',
            ])
            self.assertEqual(captured['options']['yAxis']['categories'], [
                'GLY2_B', 'SER20_B',
            ])
            self.assertFalse(captured['options']['yAxis']['reversed'])

    def test_naccess_requires_a_summary_without_runtime_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(_naccess_succeeded(root))
            summary = root / 'naccess_outputs' / 'pair' / 'Rsa_stats.csv'
            summary.parent.mkdir(parents=True)
            summary.write_text('Value\n', encoding='utf-8')
            self.assertTrue(_naccess_succeeded(root))
            self.assertFalse(_naccess_succeeded(
                root, '[WARNING] Naccess error: executable failed',
            ))

    def test_interface_patch_graph_is_exported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '_interface_patches.json').write_text(json.dumps({
                'defaultThreshold': 0.7,
                'minimumPatchSize': 3,
                'totalFrames': 10,
                'edges': [{
                    'source': {'chain': 'A', 'resNum': 10, 'resName': 'ALA'},
                    'target': {'chain': 'B', 'resNum': 20, 'resName': 'GLY'},
                    'frameCount': 8,
                    'conservation': 0.8,
                }, {
                    'source': {'chain': 'A', 'resNum': 11, 'resName': 'SER'},
                    'target': {'chain': 'B', 'resNum': 20, 'resName': 'GLY'},
                    'frameCount': 8,
                    'conservation': 0.8,
                }],
            }), encoding='utf-8')
            files = charts.generate_interface_patch_charts(
                str(root), str(root / 'charts'), 'Example',
            )
            self.assertEqual(len(files), 1)
            self.assertTrue(Path(files[0]).is_file())
            self.assertGreater(Path(files[0]).stat().st_size, 0)

    def test_legacy_two_residue_pair_is_not_exported_as_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / '_interface_patches.json').write_text(json.dumps({
                'defaultThreshold': 0.7,
                'minimumPatchSize': 2,
                'totalFrames': 10,
                'edges': [{
                    'source': {'chain': 'A', 'resNum': 10, 'resName': 'ALA'},
                    'target': {'chain': 'B', 'resNum': 20, 'resName': 'GLY'},
                    'frameCount': 8,
                }],
            }), encoding='utf-8')
            patches, _ = charts._load_interface_patches(str(root))
            self.assertEqual(patches, [])

    def test_molstar_snapshot_highlights_all_tied_largest_patches(self):
        patches = [
            {'id': 1, 'size': 3, 'residues': [
                {'chain': 'A', 'resNum': 1, 'resName': 'ALA'},
                {'chain': 'B', 'resNum': 2, 'resName': 'GLY'},
                {'chain': 'B', 'resNum': 3, 'resName': 'SER'},
            ]},
            {'id': 2, 'size': 3, 'residues': [
                {'chain': 'A', 'resNum': 10, 'resName': 'ARG'},
                {'chain': 'B', 'resNum': 20, 'resName': 'ASP'},
                {'chain': 'B', 'resNum': 21, 'resName': 'TYR'},
            ]},
            {'id': 3, 'size': 2, 'residues': [
                {'chain': 'A', 'resNum': 30, 'resName': 'ASN'},
                {'chain': 'B', 'resNum': 40, 'resName': 'GLN'},
            ]},
        ]
        captured = {}
        with patch.object(charts, '_load_interface_patches', return_value=(patches, 0.7)), patch(
            'cli.molstar_snapshot.render_molstar_snapshot',
            side_effect=lambda pdb, residues, output: captured.update(
                pdb=pdb, residues=residues, output=output,
            ) or (True, None),
        ):
            self.assertTrue(charts.generate_interface_patch_3d_snapshot(
                '/tmp/example', '/tmp/example/charts/interface_patch_3d.png',
            ))

        self.assertEqual(len(captured['residues']), 6)
        self.assertNotIn(('A', 30), {
            (item['chain'], item['resNum']) for item in captured['residues']
        })
        self.assertEqual(str(captured['pdb']), '/tmp/example/viewer.pdb')


if __name__ == '__main__':
    unittest.main()
