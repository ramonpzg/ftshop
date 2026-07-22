from chess_adapt.cli import DEFAULT_DATA_DIR, build_parser


def test_cli_exposes_independent_stages():
    args = build_parser().parse_args(["--prepare", "--enrich-limit", "2"])
    assert args.prepare is True
    assert args.qlora is False
    assert args.enrich_limit == 2
    assert args.data_dir == DEFAULT_DATA_DIR


def test_all_is_the_explicit_laptop_path():
    args = build_parser().parse_args(["--all"])
    assert args.all is True
    assert args.lora is False


def test_pull_is_available_without_selecting_a_training_method():
    args = build_parser().parse_args(["--pull"])
    assert args.pull is True
    assert args.qlora is False
    assert args.lora is False
