import pytest

from util.run_time_data_operations import RunTimeDataOperations


@pytest.fixture
def run_time_ops():
    return RunTimeDataOperations()


# Regression for issue #12: o loop interno de calculate_cliff_delta
# iterava sobre len(release_1_metrics) em vez de len(release_2_metrics),
# comparando release_1 x (slice de release_2 com tamanho de release_1).
# Quando |release_1| > |release_2| isso causa IndexError; quando
# |release_1| < |release_2| valores de release_2 sao silenciosamente
# descartados. Esses testes usam tamanhos distintos para expor o bug.


def test_cliff_delta_total_positive_separation_asymmetric_lengths(run_time_ops):
    # Todos elementos de release_1 sao maiores que todos de release_2.
    # Cliff's delta correto = +1.0 (a funcao retorna abs(), entao 1.0).
    release_1 = [10, 20, 30, 40, 50]
    release_2 = [1, 2, 3]
    assert run_time_ops.calculate_cliff_delta(release_1, release_2) == pytest.approx(
        1.0
    )


def test_cliff_delta_total_negative_separation_asymmetric_lengths(run_time_ops):
    # Todos elementos de release_1 sao menores que todos de release_2.
    # Cliff's delta correto = -1.0; com abs() vira 1.0.
    release_1 = [1, 2, 3]
    release_2 = [10, 20, 30, 40, 50]
    assert run_time_ops.calculate_cliff_delta(release_1, release_2) == pytest.approx(
        1.0
    )


def test_cliff_delta_asymmetric_known_value(run_time_ops):
    # release_1 = [1, 2, 3], release_2 = [2, 3, 4, 5].
    # Pares (x in r1, y in r2), n1*n2 = 12.
    # x>y: (3,2) -> 1 par.
    # x<y: (1,2),(1,3),(1,4),(1,5),(2,3),(2,4),(2,5),(3,4),(3,5) -> 9 pares.
    # x=y: (2,2),(3,3) -> 2 pares (contribuem 0).
    # delta = (1 - 9) / 12 = -0.6666...; abs = 0.6666...
    release_1 = [1, 2, 3]
    release_2 = [2, 3, 4, 5]
    assert run_time_ops.calculate_cliff_delta(release_1, release_2) == pytest.approx(
        8 / 12
    )


def test_remove_outliers_tira_a_amostra_atipica_das_quatro_tabelas(run_time_ops):
    import pandas as pd

    # A amostra 5 da release 2 tem chamadas muito acima das demais.
    release_1_metrics = pd.DataFrame({"metrics": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    release_2_metrics = pd.DataFrame({"metrics": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]})
    release_1_calls = pd.DataFrame({"a": [10, 11, 12, 13, 14, 15]})
    release_2_calls = pd.DataFrame({"a": [10, 11, 12, 13, 14, 500]})

    r1_metrics, r2_metrics, r1_calls, r2_calls = run_time_ops.remove_outliers(
        release_1_metrics, release_2_metrics, release_1_calls, release_2_calls
    )

    assert r1_metrics["metrics"].tolist() == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert r2_metrics["metrics"].tolist() == [1.5, 2.5, 3.5, 4.5, 5.5]
    assert r1_calls["a"].tolist() == [10, 11, 12, 13, 14]
    assert r2_calls["a"].tolist() == [10, 11, 12, 13, 14]
    assert list(r2_calls.index) == [0, 1, 2, 3, 4]


def test_remove_outliers_nao_altera_as_tabelas_recebidas(run_time_ops):
    import pandas as pd

    release_2_calls = pd.DataFrame({"a": [10, 11, 12, 13, 14, 500]})
    tabelas = [
        pd.DataFrame({"metrics": [1.0] * 6}),
        pd.DataFrame({"metrics": [2.0] * 6}),
        pd.DataFrame({"a": [10, 11, 12, 13, 14, 15]}),
        release_2_calls,
    ]

    run_time_ops.remove_outliers(*tabelas)

    assert [len(t) for t in tabelas] == [6, 6, 6, 6]
    assert release_2_calls["a"].tolist() == [10, 11, 12, 13, 14, 500]


def test_is_normalized_distingue_amostra_normal_de_assimetrica(run_time_ops):
    import numpy as np

    rng = np.random.default_rng(0)

    assert run_time_ops.is_normalized(rng.normal(50, 5, 200))
    assert not run_time_ops.is_normalized(rng.exponential(1, 200) ** 3)


def test_violation_rate_conta_as_amostras_fora_dos_limites_da_release_base(
    run_time_ops,
):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(1)
    release_1 = pd.DataFrame({"metrics": rng.normal(100, 10, 200)})
    release_2 = pd.DataFrame({"metrics": rng.normal(100, 10, 200)})
    limite_superior = release_1["metrics"].quantile(0.95)
    limite_inferior = release_1["metrics"].quantile(0.05)
    esperado = (
        (release_2["metrics"] > limite_superior)
        | (release_2["metrics"] < limite_inferior)
    ).sum() / release_2.size

    assert run_time_ops.calculate_violation_rate(release_1, release_2) == pytest.approx(
        esperado
    )


def test_violation_rate_e_none_quando_alguma_release_nao_e_normal(run_time_ops):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(2)
    normal = pd.DataFrame({"metrics": rng.normal(100, 10, 200)})
    assimetrica = pd.DataFrame({"metrics": rng.exponential(1, 200) ** 3})

    assert run_time_ops.calculate_violation_rate(normal, assimetrica) is None
