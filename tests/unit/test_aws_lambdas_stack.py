# General helper imports
import aws_cdk as core
import aws_cdk.assertions as assertions
import json

# Local helper imports
from . import ( test_api_execution ) 

# App stack import
from app import NlpLambdaStack

# Constants
expected_resources_json_path = test_api_execution.mkpath("expected_template.json")

# Test that all expected AWS resources are created, as described 
#   in the `expected_resources_json_path` file
def test_stack_resource_creation():
    # Open expected_template.json that contains expected resources
    with open(expected_resources_json_path) as json_fp:
        # Initialize app and get template
        app = core.App()
        stack = NlpLambdaStack(app, "AiidNlpLambdaStack")
        template = assertions.Template.from_stack(stack)

        # Get expected resources from json file
        expected_resources = json.load(json_fp)

        # Assert that expected_resources is list of dicts with correct attributes
        assert type(expected_resources) == list
        assert type(expected_resources[0]) == dict if len(expected_resources) > 0 else True

        # For each resource in expected_resources, check it exists with correct props
        for resource in expected_resources:
            # Check final type and shape requirements
            assert all(e in resource.keys() for e in ['Type', 'Properties'])
            assert type(resource['Properties']) == dict

            # Check that the app stack template contains this resource
            template.has_resource_properties(type=resource['Type'], props=resource['Properties'])

# example test from cdk init
# def test_sqs_queue_created():
#     app = core.App()
#     stack = NlpLambdaStack(app, "AiidNlpStack")
#     template = assertions.Template.from_stack(stack)
#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
