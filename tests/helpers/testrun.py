import subprocess
import json
import ast
import argparse
import sys
from .custom_exceptions \
    import (
        JsonException, 
        SamExecutionException, 
        SamOutputException 
    )

# inputs are expectIncident number and a ./tests/unit/testing_materials/*.json file path
#   (runs w/o redirecting output and err to files)
def run_lambda_tests(expectIncident, docsJsonPath, lambdaName='text-to-db-similar'):
    # Define command for subprocess
    cmd = ['sam', 'local', 'invoke', lambdaName, '-t', './cdk.out/AiidNlpLambdaStack.template.json', '-e', docsJsonPath]

    # Spawn subprocess and wait for its complete stdout (depending on DefaultShell argument)
    p = subprocess.Popen(' '.join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    
    stdout, err = p.communicate()

    print("stdout: ", json.loads(stdout))
    print("stderr: ", err)

    # Wait for completion
    while p.poll() == None: continue
    bestID = None

    # Normal execution
    if (p.poll() == 0):
        data = {}
        try:
            data = json.loads(json.loads(stdout))
        except:
            raise JsonException('Failure in json parsing')

        try:
            if(data["statusCode"] == 200):
                listoftupals = ast.literal_eval(data['body']['msg'])
                bestID = listoftupals[0][1]
                print("bestID output: ", bestID)
            else:
                raise SamOutputException(f"Lambda returned bad {data['statusCode']} status code, stderr: ", err)
        except:
            raise SamOutputException("Error in reading SAM output, stderr: ", err)
    else:
        raise SamExecutionException("Error in SAM execution, exit code: ", p.poll())

    return(expectIncident == bestID)

def main():
    # Initialize parser
    parser = argparse.ArgumentParser()
    
    # Adding optional argument
    parser.add_argument("-i", "--ExpectIncidentNumber", type = int, required = True, help = "Give an Expect Incident Id number")
    parser.add_argument("-d", "--DocsJson", required = True, help = "Give a ./docs .json file path")
    
    # Read arguments from command lineW
    args = parser.parse_args()

    if args.ExpectIncidentNumber and args.DocsJson:
        sys.exit(not run_text_to_db_similar_tests(args.ExpectIncidentNumber, args.DocsJson))

if __name__ == "__main__":
   main()
