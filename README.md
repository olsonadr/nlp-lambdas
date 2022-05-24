# DO NOT MERGE THIS INTO MAIN UNTIL THE STATE UPDATING HAS BEEN RE-ENABLED IN GITHUB WORKFLOWS

# AIID NLP Lambdas :hugs:
The goal of this project is to support serverless correlation of input text to similar incidents in the existing [AI Incident Database](https://incidentdatabase.ai/). This project was founded by students at Oregon State University for their 2022 Senior Capstone project.

This solution uses the [LongFormer](https://huggingface.co/allenai/longformer-base-4096) model from [Hugging Face](https://huggingface.co/) as well as the Hugging Face Transformers python library over PyTorch to accomplish the ML inference. Hugging Face Transformers is a popular open-source project that provides pre-trained, natural language processing (NLP) models for a wide variety of use cases.

Deployment of this project can be done locally or by using the included [GitHub Actions](#github-actions-for-cicd). Both require environment variables to be set, either in GitHub project secrets or using an enviroment variable file or manual variable setting, as described in the [Required Environment Variables](#required-environment-variables) section. If working locally, you will also need to manually configure your AWS credentials in the CDK CLI (discusssed in the [Prerequisites](#prerequisites) section).

The general architecture of this project was originally inspired by [this Amazon-provided sample project](https://github.com/aws-samples/zero-administration-inference-with-aws-lambda-for-hugging-face).

## Solution Overview
Our solution consists of two major segments:
 - A Python script using a pre-trained LongFormer model found in a [version-tagged git submodule](./inference/model) and PyTorch to aggregate mean CLS representations for each incident in the AIID database (currently in development, see [Future Development](#Future-Development))
 - An [AWS Cloud Development Kit](https://aws.amazon.com/cdk/) (AWS CDK) script that automatically provisions container image-based Lambda functions that perform ML inference, also using the pre-trained Longformer model. This solution also includes [Amazon Elastic File System](https://aws.amazon.com/efs/) (EFS) storage that is attached to the Lambda functions to cache the pre-trained model and the CLS means of the current DB state that reduces inference latency.

![AWS architecture diagram](./docs/aiid-nlp-lambdas-aws-architecture.png)

In this architectural diagram:
 1. Serverless inference (specifically similar-incident resolution) is achieved by using AWS Lambda functions based on Docker container images. 
 2. Each Lambda's docker container contains a saved ```pytorch_model.bin``` file and the necessary configuration files for the a pre-trained LongFormer model, which is loaded from these files by the Lambda on the first execution after deployment, and subsequently cached (in EFS, bullet 5) to accelerate subsequent invocations of the Lambda.
 3. Each Lambda's docker container also contains a pre-processed snapshot of the current state of the AIID database (in the ```state.csv``` file) as a collection of mean CLS representations which are compared against the Longformer's output for the given input text using cosine_similarity to determine similar incidents. Once loaded on first Lambda execution, this representation of the DB state is cached similarly to the model itself (bullet 2). The state representation may be updated by running ```state_update.py```, which fetches and processes new documents. This is performed automatically for deployment and testing workflows, after configuration and before bootstrapping.
 4. The container image for the Lambda is stored in an [Amazon Elastic Container Registry](https://aws.amazon.com/ecr/) (ECR) repository within your AWS account.
 5. The pre-trained Longformer model and AIID DB State are cached within Amazon Elastic File System storage in order to improve inference latency.
 6. An HTTP API is generated and hosted using AWS API Gateway to allow the Lambda(s) this project generates to be called by external users and/or future AIID applications. This is (currently) a publically accessible API that can exposes a route for each Lambda (for example, the lambda described in ```similar.py``` is given the route ```/similar```) upon which GET and POST requests can be made, providing input either using URL Query String Parameters (for GET requests) or the request body (for POST requests) as defined in the Lamda's implementation ```.py``` file.

## Prerequisites
The following is required to run/deploy this project:
-   [git](https://git-scm.com/)
-   [AWS CDK v2](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)
-   [Python](https://www.python.org/) 3.6+
-   [A virtual env](https://docs.python.org/3/library/venv.html#module-venv) (optional)

## Required Environment Variables
Deploying this project to the AWS cloud (or using the AWS CDK CLI for local development) requires several environment variables to be set for the target AWS environment to deploy to. These are required for local development as well as automatic deployment via the included GitHub Actions. 

For local development, these variables can be set in a ```.env``` file (with ```dotenv``` installed) or directly (i.e. using ```export``` command). To use the included GitHub Actions for deployment and testing, (as owner of a fork of this repo) you should configure these secrets in GitHub's repo settings. 
First you should create a new Enviroment (if it doesn't already exist) on the ```Settings >> Enviroments``` settings page, called ```aws_secrets```. Then, click on the newly created environment, and in the ```Environemnt secrets``` section, add a new secret for each of the following required variables:
 - ```AWS_ACCESS_KEY_ID```: an access key generated for your AWS root account or for an IAM user and role.
 - ```AWS_SECRET_ACCESS_KEY```: the secret-key pair of the AWS_ACCESS_KEY_ID described above.
 - ```AWS_ACCOUNT_ID```: the Account ID of the AWS account to deploy to (root account or owner of IAM user being used).
 - ```AWS_REGION```: the AWS server region to deploy the AWS application stack on (i.e. ```us-west-2```).
 - ```MONGODB_CONNECTION_STRING```: a read-enabled MONGODB connection string to allow the current database state to be read by ```inference/db_state/state_update.py``` to ensure the deployments are comparing to the most recent state of the database.

### Where to Find these AWS Credentials
This [Amazon guide](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys) talks through where to create access keys that comprise ```AWS_ACCESS_KEY_ID``` and ```AWS_SECRET_ACCESS_KEY```. The ```AWS_ACCOUNT_ID``` for a given AWS account can be found by logging into the [AWS Console](https://aws.amazon.com/), and clicking the usernmae in the top-right corner. The Account ID is (currently) the top value in the resulting dropdown list. The ```AWS_REGION``` variable must be one of the [regions supported by AWS](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/). The specific format of this region string can be found by loggin into the [AWS Console](https://aws.amazon.com/), and clicking the region dropdown in the header (just left of the far-right user dropdown). This shows a list of the available regions, paired with the shorthand names required for this variable (i.e. ```us-west-2``` for the ```US West (Oregon)``` region).

## GitHub Actions for CI/CD
This project includes a workflow designed to enable CI/CD deployment of the repo onto AWS servers. The [deployment workflow](./.github/workflows/cdk.yml) can be found in the [```.github/workflows``` directory](./.github/workflows). This project runs a series of testing actions in it's Deployment workflow as well as any pushes and a pull request to main. This is done through local environment testing through AWS SAM and ensures that both the lambda and api configuration is correct. 

## Manual/Local Deployment
1.  Clone the project to your development environment and navigate to the project directory:
    ```bash
    git clone <https://github.com/responsible-ai-collaborative/nlp-lambdas>
    cd nlp-lambdas
    ```

2.  Initialize and update the HuggingFace Longerformer model submodule:
    ```bash
    git submodule init
    git submodule update
    ```

3. Ensure all required environment variables are set acording to [Required Environment Variables](#required-environment-variables) section.
   
4. Configure AWS credentials for the CDK CLI (guide [here](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites)).

5. Update the database state representation in ```state.csv```:
    ```bash
    python ./state_update.py
    ```

6.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

7.  Bootstrap the CDK. This command provisions the initial resources
    needed by the CDK to perform deployments:
    ```bash
    cdk bootstrap
    ```

8.  This command deploys the CDK application to its environment. During
    the deployment, the toolkit outputs progress indications:
    ```bash
    cdk deploy
    ```

## Understanding the Code Structure
The code is organized using the following structure (only relevant files shown):
```bash
├── inference
│   ├── db_state
│   │   ├── incidents.csv
│   │   └── state.csv
│   ├── model
│   │   ├── config.json
│   │   ├── merges.txt
│   │   ├── tokenizer.json
│   │   └── pytorch_model.bin
│   ├── Dockerfile
│   └── similar.py
├── app.py
├── state_update.py
└── ...
```

- The ```app.py``` script is explained in the [CDK Script](#CDK-Script) section. It describes the full AWS stack of this solution and is run using the [AWS CDK v2](https://docs.aws.amazon.com/cdk/latest/) command-line to deploy the stack to AWS servers.
- The ```inference``` directory contains the files that constitute each AWS Lambda and their Docker configuration. It specifically contains:
    -   The ```Dockerfile``` used to build a custom image to be able to run PyTorch Hugging Face inference using Lambda functions and that adds the current LongFormer Model and CLS Means in the ```inference/model``` directory into the container for each lambda
    -   The Python scripts that define each AWS Lambda and perform the actual ML inference (```similar.py```)
    -   The ```db_state``` directory, which contains:
        -   The ```incidents.csv``` file that contains a downloaded snapshot of the AI Incident Database's current database of incidents. Each article is listed with all needed information about it including the raw text of the articles. This is no longer directly used to generate db_state, but is kept for testing purposes.
        -   The ```state.csv``` file which contains the current AIID DB State CLS Means used for cosine similarity comparisons with input text. This is a processed file, produced after large input text goes through the longformer model. This file is currently **required** for correct execution, but is generated by running the ```state_update.py``` script with the proper access writes to the database provided as a MongoDB connection string in the [Required Environment Variable](#required-environment-variables).
    -   The ```model``` directory, which contains:
        -   The ```config.json```, ```merges.txt```, and ```tokenizer.json``` HuggingFace boilerplate of the currently used version of the [Longformer Model HuggingFace Repo](https://huggingface.co/allenai/longformer-base-4096/tree/main)
        -   The ```pytorch_model.bin``` model file of the currently used version of the [Longformer Model HuggingFace Repo](https://huggingface.co/allenai/longformer-base-4096/tree/main). This file is **required** for correct execution, and is retrieved from the HuggingFace repository as a git submodule of this repo.

Further reading on the specifics of this project's solution can be found in the [docs/gratuitously_detailed_explanations.md](./docs/gratuitously_detailed_explanations.md) file. This file currently contains sections on the workings of the Lambda-defining [similar.py](./docs/gratuitously_detailed_explanations.md#lambda-definition-scripts-similarpy) script, our usage of the [longformer model](./docs/gratuitously_detailed_explanations.md#longformer-model), a walkthrough of the [CDK script](./docs/gratuitously_detailed_explanations.md#cdk-script).

## CDK Script
The CDK script ```app.py``` defines the architecture of the AWS application, configures the AWS resources needed for execution (i.e. Gateway API, Lambdas, Elastic File System, etc.), and describes how these resources interact, all using the CDK V2 python library. More specifics on what each portion of this script does and why can be found in [the CDK Script section of gratuitously_detailed_explanations.md](./docs/gratuitously_detailed_explanations.md#cdk-script).

## API Documentation
The AWS HTTP API this CDK application creates uses the [Lambda Proxy-Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html) standard for requests to and from the Lambdas. This necessitates specific [input](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format) and [output](api-gateway-simple-proxy-for-lambda-output-format) formats between the Lambda and the API. This format is used in the ```similar.py``` Lambda function implementation.

This is different than the request and response format specified for API Gateway <-> User communications. For these transactions, the current version of this API and Lambda Stack expects the following request and respone formats:

### ```similar.py``` API req/res formats (most similar incidents in AIID DB to input text)

#### ```similar.py``` parameters for **all** request types (currently **GET** & **POST**)
 - API endpoint: ```https:[API_URL]/similar```
 - Input variables:
     - ```text```: *required*, the input text to process
     - ```num```: *optional (default 3)*, the number of most-similar incidents to return (or -1 for all incidents in DB, ranked)
 - Relevant output variables (in HTTP response):
     - ```statusCode```: the [HTTP status code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) (i.e. 200 success, 500 error, etc.)
     - ```warnings```: list of any warning messages returned from the Lambda (incorrect but recoverable request formatting, etc.)
     - ```msg```: the requested output from the Lambda (i.e. list of tuples with similarity score and ID of that incident) or a Lambda-specified error message
 - HTTP response format:
     - Response format with output variable names as placeholders  (placeholders surrounded by **)
        ```json
        {
            "isBase64Encoded": false,
            "statusCode": *statusCode*,
            "headers": {
                "Content-Type": "application/json"
            },
            "multiValueHeaders": {},
            "body": {
                "warnings": *warnings*,
                "msg": *msg*
            }
        }
        ```
    - Response example with example values for outputs 
        ```json
        {
            "isBase64Encoded": false,
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "multiValueHeaders": {},
            "body": {
                "warnings": ["Provided value for \"num\" invalid, using default of 3."],
                "msg": "[(0.9975811839103699, 1), (0.996882975101471, 55), (0.9966274499893188, 39)]"
            }
        }
        ```
        
#### ```similar.py``` **GET** request specifics
 - Request format (uses URL query string parameters):
     - Request example with input variable names as placeholders  (placeholders surrounded by \*\*)
    ```https:[API_URL]/similar?num=*num*&text="*text*"```
     - Request example with example values (request all incidents for text "wow this is the body of a news article"):
    ```https:[API_URL]/similar?num=-1&text="Wow, this is the body of a news article!"```
     - Request example with example values (default ```num``` of 3 most similar incidents for text "wow this is the body of a news article"):
    ```https:[API_URL]/similar?num=-1&text="Wow, this is the body of a news article!"```
    

#### ```similar.py``` **POST** request specifics
 - Request body content format with input variable names as placeholders  (placeholders surrounded by \*\*)
    ```json
    {
      "text": "*text*",
      "num": *num*
    }
    ```
 - Request example with example values (request all incidents for text "wow this is the body of a news article"):
    ```json
    {
      "text": "wow this is the body of a news article",
      "num": -1
    }
    ```
- Request example with example values (default ```num``` of 3 most similar incidents for text "wow this is the body of a news article"):
    ```json
    {
      "text": "wow this is the body of a news article"
    }
    ```

## Adding additional Lambdas to the AWS App's Stack
Optionally, you can add more models by adding Python scripts in the ```inference``` directory. For example, the sample script ```docs/example_lambdas/sentiment.py``` shows how you could download and use a model from HuggingFace for sentiment analysis (would work **if and only if** you replace the internet gateway currently used with a NAT gateway -- [instructions in CDK Script section of the further reading document](./docs/gratuitously_detailed_explanations.md#cdk-script)) and without using the AWS Proxy-Integration request format:

```python
# Paraphrased for simplicity (esp. no error handling)
import json
from transformers import pipeline

# Download model from HuggingFace and store global vars in EFS cache
nlp = pipeline("sentiment-analysis")

def handler(event, context):
    result = {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": { "Content-Type": "application/json" },
        "multiValueHeaders": { },
        "body": ""
    }
    
    result['body'] = nlp(event['body']['text'])[0]
    result['statusCode'] = 200
    
    return result
```
Then run:
```bash
$ cdk synth
$ cdk deploy
```
This creates a new lambda function to perform sentiment analysis *(although you must copy the Proxy request and response structures to use this lambda with the Http API Gateway)*.

## Cleaning up
After you are finished experimenting with this project, run ```cdk destroy``` to remove all of the associated infrastructure locally and on the AWS servers. If you do not do this, and especially if you are using the NAT Gateway, you will accrue AWS charges while the Stack is hosted.

## Testing Notes
This project is automatically tested using Github Actions CI/CD, pytest, AWS CDK, and AWS Sam. Most testing checks that the end-to-end execution of the lambdas match our expected results, but one set of tests (`test_stack_resource_creation()` in `tests/unit/test_aws_lambdas_stack.py`) utilizes a json file `tests/unit/testing_materials/expected_template.json` which specifies some of the primary resources the stack should be requesting/creating in its AWS template when Synth'd in app.py. This will need to be updated if the architecture of the stack is changed, or tests will fail.

## License
This library is licensed under the MIT No Attribution License. See the [LICENSE](LICENSE) file.

Disclaimer: Deploying the applications contained in this repository will potentially cause your AWS Account to be billed for services.

## Links
- [:hugs:](https://huggingface.co)
- [AWS Cloud Development Kit](https://aws.amazon.com/cdk/)
- [Amazon Elastic Container Registry](https://aws.amazon.com/ecr/)
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [Amazon Elastic File System](https://aws.amazon.com/efs/)
