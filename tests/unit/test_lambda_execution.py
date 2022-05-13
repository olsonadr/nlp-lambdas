import pytest
import os.path
from ..helpers import testrun
from ..helpers.custom_exceptions \
    import (
        JsonException,
        SamOutputException
    )

path_to_project_root = "."
json_dir_from_project_root = "docs"

# Shorthand helper for creating paths to test json files
def mkpath(json_filename: str):
    return os.path.join(path_to_project_root,
                        json_dir_from_project_root,
                        json_filename)

def test_good_execution():
    assert testrun.runTestPipeTest(1, mkpath("example_invoke_long.json"))
    assert testrun.runTestPipeTest(15, mkpath("example_test_data_15.json"))

def test_incorrect_value():
    assert not testrun.runTestPipeTest(-5, mkpath("example_test_data_15.json"))

def test_json_input_syntax_error():
    with pytest.raises(JsonException):
        testrun.runTestPipeTest(1, mkpath("example_test_data_bad_json.json"))

def test_missing_required_input_field():
    with pytest.raises(SamOutputException):
        testrun.runTestPipeTest(1, mkpath("example_test_data_missing_input.json"))

# Additional tests might include
#   - checking that bestOf=N parameter correctly gives N results