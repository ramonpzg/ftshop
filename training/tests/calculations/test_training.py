import pytest

from chess_adapt.calculations.training import check_vram, repository_for


def test_q_lora_fits_the_presenter_gpu_boundary():
    check_vram("qlora", 7.99, free_gib=7.2)


def test_q_lora_refuses_when_llama_cpp_is_still_using_the_gpu():
    with pytest.raises(RuntimeError, match="Stop llama.cpp"):
        check_vram("qlora", 7.99, free_gib=5.4)


def test_full_precision_lora_refuses_an_eight_gib_gpu():
    with pytest.raises(RuntimeError, match="base checkpoint alone is about 10.2 GB"):
        check_vram("lora", 7.99)


def test_force_vram_is_explicit_and_repo_names_do_not_collide():
    check_vram("lora", 7.99, force=True)
    assert repository_for("ramonpzg/gemma-4-e2b-chessking", "qlora") == (
        "ramonpzg/gemma-4-e2b-chessking"
    )
    assert repository_for("ramonpzg/gemma-4-e2b-chessking", "lora").endswith("-lora")
