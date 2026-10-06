from cli.main import build_parser


def test_web_conservation_slider_flags_are_independent():
    args = build_parser().parse_args([
        "trajectory.pdb",
        "--pair-conservation", "50",
        "--interaction-conservation", "40",
    ])

    assert args.pair_conservation == 50
    assert args.interaction_conservation == 40


def test_legacy_threshold_flag_remains_pair_conservation_alias():
    args = build_parser().parse_args(["trajectory.pdb", "-t", "65"])

    assert args.pair_conservation == 65
    assert args.interaction_conservation is None
