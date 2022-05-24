import os.path
from ..helpers import apitest

path_to_project_root = "."
json_dir_from_project_root = ["tests", "unit", "testing_materials"]

# Shorthand helper for creating paths to test json files
def mkpath(json_filename: str):
    return os.path.join(path_to_project_root,
                        *json_dir_from_project_root,
                        json_filename)

def test_good_text_to_db_similar_execution():
    assert apitest.run_api_tests(1, mkpath("lambda_test_request_incident_1.json"), payloadKey="text", route="/text-to-db-similar")
    assert apitest.run_api_tests(15, mkpath("lambda_test_request_incident_15.json"), payloadKey="text", route="/text-to-db-similar")
    assert apitest.run_api_tests(10, mkpath("lambda_test_request_incident_10.json"), payloadKey="text", route="/text-to-db-similar")

def test_good_embed_to_db_similar_execution():
    assert apitest.run_api_tests(1, mkpath("lambda_test_request_incident_1_embedding.json"), payloadKey="embed", route="/embed-to-db-similar")
    assert apitest.run_api_tests(15, mkpath("lambda_test_request_incident_15_embedding.json"), payloadKey="embed", route="/embed-to-db-similar")
    assert apitest.run_api_tests(10, mkpath("lambda_test_request_incident_10_embedding.json"), payloadKey="embed", route="/embed-to-db-similar")

def test_incorrect_text_to_db_similar_value():
    assert not apitest.run_api_tests(-5, mkpath("lambda_test_request_incident_15.json"), payloadKey="text", route="/text-to-db-similar")

def test_incorrect_embed_to_db_similar_value():
    assert not apitest.run_api_tests(-5, mkpath("lambda_test_request_incident_15_embedding.json"), payloadKey="embed", route="/embed-to-db-similar")

# Additional tests might include
#   - checking that bestOf=N parameter correctly gives N results
#   - looking for custom exceptions on bad inputs