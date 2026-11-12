import numpy as np
import pytest

from util.check import Checker
from util.exceptions import (
    InvalidCheckThreshold,
    InvalidMetricValue,
    InvalidReleaseMatrix,
    InvalidThresholdValue,
)


def test_check_threshold_sem_funcao_para_a_medida():
    with pytest.raises(InvalidCheckThreshold, match="Check function not implemented"):
        Checker.check_threshold(0, 1, "medida_inexistente")


def test_check_metric_values_exige_lista_ou_array():
    with pytest.raises(
        InvalidMetricValue, match='"ncloc" is not a list or a np.ndarray'
    ):
        Checker.check_metric_values("10", "ncloc")


@pytest.mark.parametrize(
    "rd",
    [
        np.array([[0.5, 0.5], [0.5, 0.5]]),  # só 2 releases
        np.array([[0.5], [0.5], [0.5]]),  # só 1 característica
        np.array([0.5, 0.5, 0.5]),  # não é matriz
    ],
)
def test_release_matrix_com_formato_invalido(rd):
    with pytest.raises(
        InvalidReleaseMatrix, match="at least 3 releases and 2 characteristics"
    ):
        Checker.check_release_matrix(rd)


@pytest.mark.parametrize("valor", [np.nan, -0.1, 1.1])
def test_release_matrix_com_valor_fora_de_0_a_1(valor):
    rd = np.array([[0.5, 0.5], [0.5, valor], [0.5, 0.5]])

    with pytest.raises(InvalidReleaseMatrix, match="between 0 and 1"):
        Checker.check_release_matrix(rd)


def test_release_matrix_valida():
    Checker.check_release_matrix(np.array([[0.0, 1.0], [0.5, 0.5], [1.0, 0.0]]))


@pytest.mark.parametrize(
    "medida, minimo, maximo, mensagem",
    [
        ("team_throughput", 40, 100, "min_threshold is not equal to 45"),
        ("team_throughput", 45, 90, "max_threshold is not equal to 100"),
        ("ci_feedback_time", 0, 900, "min_threshold is not equal to 1"),
        ("ci_feedback_time", 1, 600, "max_threshold is not equal to 900"),
    ],
)
def test_limites_fixos_das_medidas_de_processo(medida, minimo, maximo, mensagem):
    with pytest.raises(InvalidThresholdValue, match=mensagem):
        Checker.check_threshold(minimo, maximo, medida)


@pytest.mark.parametrize(
    "medida, minimo, maximo",
    [("team_throughput", 45, 100), ("ci_feedback_time", 1, 900)],
)
def test_limites_validos_das_medidas_de_processo(medida, minimo, maximo):
    Checker.check_threshold(minimo, maximo, medida)


@pytest.mark.parametrize(
    "minimo, maximo, mensagem",
    [
        (1, 10, "min_threshold is not equal to 0"),
        (0, 0, "min_threshold is greater or equal to max_threshold"),
    ],
)
def test_fast_test_builds_segue_as_regras_da_non_complex_files_density(
    minimo, maximo, mensagem
):
    with pytest.raises(InvalidThresholdValue, match=mensagem):
        Checker.check_threshold(minimo, maximo, "fast_test_builds")

    Checker.check_threshold(0, 300000, "fast_test_builds")
