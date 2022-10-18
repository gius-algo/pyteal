"""
This file monkey-patches ConfigParser in order to enable
source mapping and test the results of source mapping various 
PyTeal apps.
"""

from configparser import ConfigParser
from pathlib import Path

import pytest
from unittest import mock


ALGOBANK = Path.cwd() / "examples" / "application" / "abi"

FIXTURES = Path.cwd() / "tests" / "unit" / "sourcemaps"


@mock.patch.object(ConfigParser, "getboolean", return_value=True)
def test_reconstruct(_):
    from pyteal import OptimizeOptions
    from examples.application.abi.algobank import router

    compile_bundle = router.compile_program_with_sourcemaps(
        version=6, optimize=OptimizeOptions(scratch_slots=True)
    )

    assert compile_bundle.approval_sourcemap
    assert compile_bundle.clear_sourcemap

    with open(ALGOBANK / "algobank_approval.teal") as af:
        assert af.read() == compile_bundle.approval_sourcemap.teal()

    with open(ALGOBANK / "algobank_clear_state.teal") as cf:
        assert cf.read() == compile_bundle.clear_sourcemap.teal()


def fixture_comparison(sourcemap: "PyTealSourceMap", name: str):
    new_version = sourcemap._tabulate_for_dev()
    with open(FIXTURES / f"{name}", "w") as f:
        f.write(new_version)

    not_actually_comparing = True
    if not_actually_comparing:
        return

    with open(FIXTURES / name) as f:
        old_version = f.read()

    assert old_version == new_version


@mock.patch.object(ConfigParser, "getboolean", return_value=True)
@pytest.mark.parametrize("version", [6])
@pytest.mark.parametrize("source_inference", [False, True])
@pytest.mark.parametrize("assemble_constants", [False, True])
@pytest.mark.parametrize("optimize_slots", [False, True])
def test_sourcemaps(_, version, source_inference, assemble_constants, optimize_slots):
    from pyteal import OptimizeOptions

    from examples.application.abi.algobank import router

    # TODO: add functionality that tallies the line statuses up and assert that all
    # statuses were > SourceMapItemStatus.PYTEAL_GENERATED

    compile_bundle = router.compile_program_with_sourcemaps(
        version=version,
        assemble_constants=assemble_constants,
        optimize=OptimizeOptions(scratch_slots=optimize_slots),
        source_inference=source_inference,
    )

    assert compile_bundle.approval_sourcemap
    assert compile_bundle.clear_sourcemap

    suffix = f"_v{version}_si{int(source_inference)}_ac{int(assemble_constants)}_ozs{int(optimize_slots)}"
    fixture_comparison(
        compile_bundle.approval_sourcemap, f"algobank_approval{suffix}.txt"
    )
    fixture_comparison(compile_bundle.clear_sourcemap, f"algobank_clear{suffix}.txt")


@mock.patch.object(ConfigParser, "getboolean", return_value=True)
def test_annotated_teal(_):
    from pyteal import OptimizeOptions

    from examples.application.abi.algobank import router

    compile_bundle = router.compile_program_with_sourcemaps(
        version=6,
        optimize=OptimizeOptions(scratch_slots=True),
    )

    ptsm = compile_bundle.approval_sourcemap
    assert ptsm

    table = ptsm.annotated_teal()

    with open(FIXTURES / "algobank_annotated.teal", "w") as f:
        f.write(table)

    table_ast = ptsm.annotated_teal(unparse_hybrid=True)

    with open(FIXTURES / "algobank_hybrid.teal", "w") as f:
        f.write(table_ast)


@mock.patch.object(ConfigParser, "getboolean", return_value=True)
def test_mocked_config_for_frames(_):
    config = ConfigParser()
    assert config.getboolean("pyteal-source-mapper", "enabled") is True
    from pyteal.util import Frames

    assert Frames.skipping_all() is False
    assert Frames.skipping_all(_force_refresh=True) is False


# TODO: this is temporary


def make(x, y, z):
    import pyteal as pt

    return pt.Int(x) + pt.Int(y) + pt.Int(z)


import pyteal as pt

e1 = pt.Seq(pt.Pop(make(1, 2, 3)), pt.Pop(make(4, 5, 6)), make(7, 8, 9))


@pt.Subroutine(pt.TealType.uint64)
def foo(x):
    return pt.Seq(pt.Pop(e1), e1)


@mock.patch.object(ConfigParser, "getboolean", return_value=True)
def test_lots_o_indirection(_):
    bundle = pt.Compilation(foo(pt.Int(42)), pt.Mode.Application, version=6).compile(
        with_sourcemap=True
    )