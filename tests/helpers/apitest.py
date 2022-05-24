import requests
import ast
import subprocess
import json
import argparse
import time
import sys
from iterators import TimeoutIterator
import psutil
import atexit

from .custom_exceptions import (InternalServerException, StartApiTimeoutException)

start_api_timeout = 60
request_timeout = 180
api_running = False
p_list = []

# Source: https://stackoverflow.com/a/25134985
def kill(proc_pid):
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()

# Source: https://stackoverflow.com/a/320712
@atexit.register
def cleanup():
    global p_list
    global api_running
    timeout_sec = 1
    p_sec = 0
    for p in p_list:
        for second in range(timeout_sec):
            if p.poll() == None:
                time.sleep(1)
                p_sec += 1
        if p_sec >= timeout_sec and p:
            kill(p.pid)
            p.kill()
    p_list = []
    api_running = False

def run_api_tests(expectIncident, docsJsonPath, payloadKey='text', route='/text-to-db-similar'):
    # register global
    global p_list
    global api_running

    # start the api
    p = start_api()
    p_list.append(p)

    # initial, failing values
    res_get = -1
    res_post = -2

    # try to make test requests
    try:
        if api_running:
            # Open the provided json input and run a get and post request
            with open(docsJsonPath, encoding="utf-8") as json_file:
                res_get = run_get_test_fd(expectIncident, json_file, payloadKey, route)
                json_file.seek(0)
                res_post = run_post_test_fd(expectIncident, json_file, route)
    except Exception as e:
        api_running = False
        cleanup()
        raise e

    if p:
        kill(p.pid)
        out, err = p.communicate()
        api_running = False

    return(res_get == res_post == True)

def start_api():
    global api_running
    global start_api_timeout

    if not api_running:
        # Run start-api command as subprocess
        cmd = ['sam', 'local', 'start-api', '-t', './cdk.out/AiidNlpLambdaStack.template.json']
        p = subprocess.Popen(' '.join(cmd), stderr=subprocess.PIPE, shell=True, universal_newlines=True)

        # Wait for api to be running
        it = TimeoutIterator(p.stderr, timeout=start_api_timeout)
        for line in it:
            print(line)
            if line == it.get_sentinel():
                kill(p.pid)
                _, _ = p.communicate()
                it.interrupt()
                raise StartApiTimeoutException
            elif "(Press CTRL+C to quit)" in str(line):
                it.interrupt()
                break
        
        api_running = True
        return p

    return None

def run_get_test_path(expectIncident, docsJsonPath, payloadKey="text", route="/text-to-db-similar"):
    with open(docsJsonPath, encoding="utf-8") as json_file:
        return run_get_test_fd(expectIncident, json_file, payloadKey, route)
    return False

def run_get_test_fd(expectIncident, json_file, payloadKey="text", route="/text-to-db-similar"):
    json_payload = json.load(json_file)
    get_payload = json_payload[payloadKey]
    get_url = (f'http://127.0.0.1:3000{route}?{payloadKey}="{get_payload}"')
    get_url_shortened = get_url if len(get_url)<100 else f'{get_url[:90]} ... {get_url[-10:]}'
    print(f"before request, req_url = {get_url_shortened}")
    res = requests.get(get_url, timeout=request_timeout)
    print(f"after request, res = {res}")
    print(res.json())

    # Parse json response
    res_json = json.loads(res.text)

    # Check for success
    if 'body' not in res_json:
        # Internal server error :(
        print("Lambda handler had unexpected runtime error, resulting in a \"Internal Server Error\" response from the API")
        raise InternalServerException
    elif 'statusCode' not in res_json:
        # Unkown error
        print("Unknown error, but statusCode was not given back in response")
        raise Exception
    elif res_json['statusCode'] != 200:
        # Handled error in lambda execution
        print(f"Lambda handler had expected runtime error {res_json['statusCode']} w/ body \"{res_json['body']['msg']}\"")
        raise InternalServerException
    else:
        # Successful! Get output and return if correct.
        getOutputIncident = ast.literal_eval(res_json['body']['msg'])[0][1]
        print(getOutputIncident)
        return (getOutputIncident == expectIncident)

def run_post_test_path(expectIncident, docsJsonPath, route="/text-to-db-similar"):
    with open(docsJsonPath, encoding="utf-8") as json_file:
        return run_post_test_fd(expectIncident, json_file, route)
    return False

def run_post_test_fd(expectIncident, json_file, route="/text-to-db-similar"):
    json_payload = json.load(json_file)
    # print(f"req: {json_payload}")
    res = requests.post(f"http://127.0.0.1:3000{route}", json=json_payload, timeout=request_timeout)
    print(f"res = {res}")
    print(res.json())

    # Parse json response
    res_json = json.loads(res.text)

    # Check for success
    if 'body' not in res_json:
        # Internal server error :(
        print("Lambda handler had unexpected runtime error, resulting in a \"Internal Server Error\" response from the API")
        raise InternalServerException
    elif 'statusCode' not in res_json:
        # Unkown error
        print("Unknown error, but statusCode was not given back in response")
        raise Exception
    elif res_json['statusCode'] != 200:
        # Handled error in lambda execution
        print(f"Lambda handler had expected runtime error {res_json['statusCode']} w/ body \"{res_json['body']['msg']}\"")
        raise InternalServerException
    else:
        # Successful! Get output and return if correct.
        postOutputIncident = ast.literal_eval(json.loads(res.text)['body']['msg'])[0][1]
        print(postOutputIncident)
        return (postOutputIncident == expectIncident)


def main():
     # Initialize parser
    parser = argparse.ArgumentParser()
    
    # Adding optional argument
    parser.add_argument("-i", "--ExpectIncidentNumber", type = int, required = True, help = "Give an Expect Incident Id number")
    parser.add_argument("-d", "--DocsJson", required = True, help = "Give a ./docs .json file path")
    
    # Read arguments from command lineW
    args = parser.parse_args()

    if args.ExpectIncidentNumber and args.DocsJson:
        sys.exit(not run_api_tests(args.ExpectIncidentNumber, args.DocsJson))


if __name__ == "__main__":
    main()