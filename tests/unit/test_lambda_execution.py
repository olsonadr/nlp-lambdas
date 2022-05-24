import pytest
import os.path
from ..helpers import testrun
from ..helpers.custom_exceptions \
    import (
        JsonException,
        SamOutputException
    )

path_to_project_root = "."
json_dir_from_project_root = ["tests", "unit", "testing_materials"]

# Shorthand helper for creating paths to test json files
def mkpath(json_filename: str):
    return os.path.join(path_to_project_root,
                        *json_dir_from_project_root,
                        json_filename)

def test_good_text_to_db_similar_execution():
    assert testrun.run_lambda_tests(1, mkpath("lambda_test_request_incident_1.json"), lambdaName="text-to-db-similar")
    assert testrun.run_lambda_tests(15, mkpath("lambda_test_request_incident_15.json"), lambdaName="text-to-db-similar")
    assert testrun.run_lambda_tests(10, mkpath("lambda_test_request_incident_10.json"), lambdaName="text-to-db-similar")
    
def test_good_embed_to_db_similar_execution():
    assert testrun.run_lambda_tests(1, mkpath("lambda_test_request_incident_1_embedding.json"), lambdaName="embed-to-db-similar")
    assert testrun.run_lambda_tests(15, mkpath("lambda_test_request_incident_15_embedding.json"), lambdaName="embed-to-db-similar")
    assert testrun.run_lambda_tests(10, mkpath("lambda_test_request_incident_10_embedding.json"), lambdaName="embed-to-db-similar")

def test_incorrect_text_to_db_similar_value():
    assert not testrun.run_lambda_tests(-5, mkpath("lambda_test_request_incident_15.json"), lambdaName="text-to-db-similar")

def test_incorrect_embed_to_db_similar_value():
    assert not testrun.run_lambda_tests(-5, mkpath("lambda_test_request_incident_15_embedding.json"), lambdaName="embed-to-db-similar")

def test_json_input_syntax_error_text_to_db_similar_():
    with pytest.raises(JsonException):
        testrun.run_lambda_tests(1, mkpath("lambda_bad_test_request_bad_syntax.json"), lambdaName="text-to-db-similar")

def test_json_input_syntax_error_embed_to_db_similar_():
    with pytest.raises(JsonException):
        testrun.run_lambda_tests(1, mkpath("lambda_bad_test_request_bad_syntax.json"), lambdaName="embed-to-db-similar")

def test_missing_required_input_field_text_to_db_similar_():
    with pytest.raises(SamOutputException):
        testrun.run_lambda_tests(1, mkpath("lambda_bad_test_request_missing_input.json"), lambdaName="text-to-db-similar")
        
def test_missing_required_input_field_embed_to_db_similar_():
    with pytest.raises(SamOutputException):
        testrun.run_lambda_tests(1, mkpath("lambda_bad_test_request_missing_input.json"), lambdaName="embed-to-db-similar")

# Additional tests might include
#   - checking that bestOf=N parameter correctly gives N results