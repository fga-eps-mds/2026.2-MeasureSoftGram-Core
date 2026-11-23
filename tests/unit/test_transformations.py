import pytest
from core.transformations import (
    GainInterpretation,
    correlation_function,
    diff,
    interpretation_function,
    norm_diff,
)
from tests.utils.transformations_data import (
    EXAMPLE_7_RD,
    EXAMPLE_7_RD_CORR,
    INVALID_DIFF_DATA,
    INVALID_RELEASE_MATRIX_DATA,
    NORMAL_RD,
    NORMAL_RD_CORR,
    VALID_DIFF_DATA,
)
from util.exceptions import (
    InvalidGainInterpretationValue,
    InvalidReleaseMatrix,
    ReleasePlannedAndDevelopedOfDifferentSizes,
)
import numpy as np


@pytest.mark.parametrize(
    "rp,rd,error_msg",
    INVALID_DIFF_DATA,
)
def test_norm_diff_failure(rp, rd, error_msg):
    rp = np.array(rp)
    rd = np.array(rd)
    with pytest.raises((ReleasePlannedAndDevelopedOfDifferentSizes)) as error:
        norm_diff(rp=rp, rd=rd)
    assert str(error.value) == error_msg


@pytest.mark.parametrize(
    "rp,rd,error_msg",
    INVALID_DIFF_DATA,
)
def test_diff_failure(rp, rd, error_msg):
    rp = np.array(rp)
    rd = np.array(rd)
    with pytest.raises((ReleasePlannedAndDevelopedOfDifferentSizes)) as error:
        diff(rp=rp, rd=rd)
    assert str(error.value) == error_msg


@pytest.mark.parametrize(
    "rp,rd,res",
    VALID_DIFF_DATA,
)
def test_norm_diff_valid(rp, rd, res):
    rp = np.array(rp)
    rd = np.array(rd)
    assert pytest.approx(norm_diff(rp, rd)) == res[0]


@pytest.mark.parametrize(
    "rp,rd,res",
    VALID_DIFF_DATA,
)
def test_diff_valid(rp, rd, res):
    rp = np.array(rp)
    rd = np.array(rd)
    assert pytest.approx(diff(rp, rd)) == res[1]


def test_correlation_function_example_7():
    result = correlation_function(np.array(EXAMPLE_7_RD))

    assert result["method"] == "spearman"
    assert result["normal"] == [False] * 8
    assert np.round(result["coefficients"], 2).tolist() == EXAMPLE_7_RD_CORR


def test_correlation_function_normal_rd():
    result = correlation_function(np.array(NORMAL_RD))

    assert result["method"] == "pearson"
    assert result["normal"] == [True] * 3
    assert np.round(result["coefficients"], 4).tolist() == NORMAL_RD_CORR


def test_correlation_function_p_values():
    result = correlation_function(np.array(EXAMPLE_7_RD))

    # Com 20 releases, p < 0,05 equivale a |r| > 0,44.
    assert result["p_values"][0][7] > 0.05
    assert result["p_values"][2][5] < 0.05
    assert result["p_values"][2][3] == result["p_values"][3][2]


def test_correlation_function_constant_column():
    rd = np.array(NORMAL_RD)
    rd[:, 1] = 0.5

    result = correlation_function(rd)

    assert result["method"] == "spearman"
    assert result["normal"] == [True, False, True]
    assert result["coefficients"][1] == [None, None, None]
    assert [row[1] for row in result["coefficients"]] == [None, None, None]
    assert result["p_values"][0][1] is None
    assert result["coefficients"][0][2] is not None


@pytest.mark.parametrize(
    "rd,error_msg",
    INVALID_RELEASE_MATRIX_DATA,
)
def test_correlation_function_invalid_release_matrix(rd, error_msg):
    with pytest.raises(InvalidReleaseMatrix) as error:
        correlation_function(np.array(rd))
    assert str(error.value) == error_msg


@pytest.mark.parametrize(
    "x,gain_interpretation,expected",
    [
        (0.5, 1, 0.5),
        (0.2, -1, 0.8),
        (0.2, GainInterpretation.POSITIVE_SLOPE, 0.2),
        (0.2, GainInterpretation.NEGATIVE_SLOPE, 0.8),
        (np.array([0.0, 0.25, 1.0]), -1, [1.0, 0.75, 0.0]),
    ],
)
def test_interpretation_function_valid_gain(x, gain_interpretation, expected):
    result = interpretation_function(
        x=x,
        min_threshold=0,
        max_threshold=1,
        gain_interpretation=gain_interpretation,
    )
    assert np.allclose(result, expected)


@pytest.mark.parametrize("gain_interpretation", [0, 2, -2, None, "1"])
def test_interpretation_function_invalid_gain(gain_interpretation):
    with pytest.raises(InvalidGainInterpretationValue) as error:
        interpretation_function(
            x=0.5,
            min_threshold=0,
            max_threshold=1,
            gain_interpretation=gain_interpretation,
        )
    assert str(error.value) == (
        f"Gain Interpretation need be 1 or -1, but received {gain_interpretation}"
    )
