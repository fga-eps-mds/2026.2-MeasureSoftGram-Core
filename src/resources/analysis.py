from enum import Enum
import numpy as np
from marshmallow.exceptions import ValidationError
from marshmallow.utils import INCLUDE

from core.schemas import (
    CalculateCharacteristicSchema,
    CalculateMeasureSchema,
    CalculateRuntimeMeasureSchema,
    CalculateSubCharacteristicSchema,
    CalculateTSQMISchema,
)
from core.transformations import calculate_aggregated_weighted_value
from resources.constants import AGGREGATED_NORMALIZED_MEASURES_MAPPING
from util.exceptions import MeasureKeyNotSupported

MEASURE_TYPE = Enum("MEASURE_TYPE", ["STATIC", "RUN_TIME"])


def convert_metrics_to_dict(metrics_list):
    metrics_dict = {}
    for metric in metrics_list:
        if len(metric["value"]) == 1:
            metrics_dict[metric["key"]] = float(metric["value"][0])
        else:
            metrics_dict[metric["key"]] = metric["value"]

    return metrics_dict


def _load_extracted_measures(extracted_measures):
    """Valida a entrada como medidas estáticas ou de tempo de execução."""
    if not CalculateMeasureSchema().validate(extracted_measures):
        return CalculateMeasureSchema().load(extracted_measures), MEASURE_TYPE.STATIC

    if not CalculateRuntimeMeasureSchema().validate(extracted_measures):
        return (
            CalculateRuntimeMeasureSchema().load(extracted_measures),
            MEASURE_TYPE.RUN_TIME,
        )

    raise ValidationError("error: Extracted measures are not formatted correctly")


def _validate_measure_params(measure_key: str, measure: dict, measure_type):
    """Carrega a medida pelo schema dela e roda as validações específicas de métricas."""
    schema = AGGREGATED_NORMALIZED_MEASURES_MAPPING[measure_key]["schema"]()

    try:
        validated_params = schema.load(data=measure, unknown=INCLUDE)
        validate_metrics = getattr(schema, "validate_metrics", None)
        if callable(validate_metrics):
            validate_metrics(
                validated_params["metrics"]
                if measure_type == MEASURE_TYPE.STATIC
                else validated_params
            )
    except ValidationError as exc:
        raise ValidationError(
            f"error: Metrics in {measure_key} are not valid.\nschema_errors: {exc.messages}"
        )

    if measure_type == MEASURE_TYPE.STATIC:
        return convert_metrics_to_dict(validated_params["metrics"])
    return validated_params


def _threshold_config(config: dict, measure_key: str) -> dict:
    """Limites (min_threshold e max_threshold) que a configuração define para a medida."""
    return {
        key: value
        for characteristic in config["characteristics"]
        for subcharacteristic in characteristic["subcharacteristics"]
        for measure in subcharacteristic["measures"]
        if measure["key"] == measure_key
        for key, value in measure.items()
        if key in ("min_threshold", "max_threshold")
    }


def calculate_measures(
    extracted_measures: CalculateMeasureSchema | CalculateRuntimeMeasureSchema,
    config: dict = {
        "characteristics": [{"subcharacteristics": [{"measures": [{"key": ""}]}]}]
    },
):
    data, measure_type = _load_extracted_measures(extracted_measures)

    # Objeto retornado em caso de sucesso
    result_data = {"measures": []}

    for measure in data["measures"]:
        measure_key: str = measure["key"]

        if measure_key not in AGGREGATED_NORMALIZED_MEASURES_MAPPING:
            raise MeasureKeyNotSupported(f"Measure {measure_key} is not supported")

        validated_params = _validate_measure_params(measure_key, measure, measure_type)

        aggregated_normalized_measure = AGGREGATED_NORMALIZED_MEASURES_MAPPING[
            measure_key
        ]["aggregated_normalized_measure"]

        result = aggregated_normalized_measure(
            validated_params, **_threshold_config(config, measure_key)
        )

        result_data["measures"].append(
            {
                "key": measure_key,
                "value": result,
            }
        )

    return result_data


def calculate_subcharacteristics(extracted_subcharacteristics):
    try:
        data = CalculateSubCharacteristicSchema().load(extracted_subcharacteristics)
    except ValidationError as error:
        raise ValidationError(
            f"error: Failed to validate input.\nschema_errors: {error.messages}"
        )

    result_data = {"subcharacteristics": []}

    for subcharacteristic in data["subcharacteristics"]:
        subcharacteristic_key: str = subcharacteristic["key"]

        vector_aggregated_normalized_measure = np.array([])
        vector_weight_aggregated_normalized_measure = np.array([])

        for measure in subcharacteristic["measures"]:
            vector_aggregated_normalized_measure = np.append(
                vector_aggregated_normalized_measure, measure["value"]
            )
            vector_weight_aggregated_normalized_measure = np.append(
                vector_weight_aggregated_normalized_measure, measure["weight"]
            )
        aggregated_value = calculate_aggregated_weighted_value(
            vector_aggregated_normalized_measure,
            vector_weight_aggregated_normalized_measure,
        )

        result_data["subcharacteristics"].append(
            {
                "key": subcharacteristic_key,
                "value": aggregated_value,
            }
        )

    return result_data


def calculate_characteristics(extracted_characteristics):
    try:
        data = CalculateCharacteristicSchema().load(extracted_characteristics)
    except ValidationError as error:
        raise ValidationError(
            f"error: Failed to validate input.\nschema_errors: {error.messages}"
        )

    result_data = {"characteristics": []}

    for characteristic in data["characteristics"]:
        characteristic_key: str = characteristic["key"]

        vector_aggregated_normalized_subcharacteristics = np.array([])
        vector_weight_aggregated_normalized_subcharacteristics = np.array([])
        for subcharacteristics in characteristic["subcharacteristics"]:
            vector_aggregated_normalized_subcharacteristics = np.append(
                vector_aggregated_normalized_subcharacteristics,
                subcharacteristics["value"],
            )
            vector_weight_aggregated_normalized_subcharacteristics = np.append(
                vector_weight_aggregated_normalized_subcharacteristics,
                subcharacteristics["weight"],
            )

        aggregated_value = calculate_aggregated_weighted_value(
            vector_aggregated_normalized_subcharacteristics,
            vector_weight_aggregated_normalized_subcharacteristics,
        )

        result_data["characteristics"].append(
            {
                "key": characteristic_key,
                "value": aggregated_value,
            }
        )

    return result_data


def calculate_tsqmi(extracted_tsqmi):
    try:
        data = CalculateTSQMISchema().load(extracted_tsqmi)
    except ValidationError as error:
        raise ValidationError(
            f"error: Failed to validate input.\nschema_errors: {error.messages}"
        )

    result_data = {"tsqmi": []}

    tsqmi = data["tsqmi"]
    tsqmi_key: str = tsqmi["key"]

    vector_aggregated_normalized_characteristics = np.array([])
    vector_weight_aggregated_normalized_characteristics = np.array([])
    for characteristic in tsqmi["characteristics"]:
        vector_aggregated_normalized_characteristics = np.append(
            vector_aggregated_normalized_characteristics, characteristic["value"]
        )
        vector_weight_aggregated_normalized_characteristics = np.append(
            vector_weight_aggregated_normalized_characteristics,
            characteristic["weight"],
        )

    aggregated_value = calculate_aggregated_weighted_value(
        vector_aggregated_normalized_characteristics,
        vector_weight_aggregated_normalized_characteristics,
    )

    result_data["tsqmi"].append(
        {
            "key": tsqmi_key,
            "value": aggregated_value,
        }
    )

    return result_data
