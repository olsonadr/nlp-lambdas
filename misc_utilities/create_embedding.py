# Imports
from ast import literal_eval
import os
import json
import os
import pandas as pd
import torch
from transformers import LongformerTokenizer, LongformerModel
from unidecode import unidecode
import pandas as pd
from typing import Union

model = LongformerModel.from_pretrained(
    './inference/model', local_files_only=True)
tokenizer = LongformerTokenizer.from_pretrained(
    './inference/model', local_files_only=True)
csv_path = './inference/db_state/incidents.csv'
incidents_path = './inference/db_state/state.csv'
best_of_def = 3

# Load in a list of incident states from a CSV
state = pd.read_csv(incidents_path, converters={"mean": literal_eval})

# Get longformer embedding
def get_embedding(text:str):
    inp = tokenizer(text,
                    padding="longest",
                    truncation="longest_first",
                    return_tensors="pt")
    return model(**inp).last_hidden_state[0][0]

# Compute cosine similarity between two tensors
# Returns a single value of the cosine_sim
def compute_cosine_sim_e_e(embed_1: Union[torch.Tensor,list], embed_2: Union[torch.Tensor,list]):
    embed_1 = embed_1 if type(embed_1) == torch.Tensor else torch.tensor(embed_1)
    embed_2 = embed_2 if type(embed_2) == torch.Tensor else torch.tensor(embed_2)
    return torch.nn.functional.cosine_similarity(embed_1, embed_2, dim=-1)

# Compute cosine similarity between a tensor and all embeddings in a db state DataFrame
# Returns a list of tuples (cosine_sim, incident_id) for each incident in dataframe
def compute_cosine_sim_e_df(embed: Union[torch.Tensor,list], dataframe: pd.DataFrame):
    embed = embed if type(embed) == torch.Tensor else torch.tensor(embed)
    return [(
                compute_cosine_sim_e_e(embed, torch.tensor(dataframe.loc[i, "mean"])).item(),
                dataframe.loc[i, "incident_id"]
            ) for i in range(len(state))]

# Process input text for text-to-db-similar computation
# Returns a list of the most N (best_of) similar incidents with scores and IDs
def process_input_text(text: str, best_of: int = best_of_def):
    embed = get_embedding(text)
    cosine_sims = sorted(compute_cosine_sim_e_df(embed, state), reverse=True)
    if (best_of >= 0):
        return cosine_sims[:best_of]
    else:
        return cosine_sims

# Process input text for text-to-db-similar computation
# Returns a list of the most N (best_of) similar incidents with scores and IDs
def process_input_list(embed: list, best_of: int = best_of_def):
    cosine_sims = sorted(compute_cosine_sim_e_df(embed, state), reverse=True)
    if (best_of >= 0):
        return cosine_sims[:best_of]
    else:
        return cosine_sims

# Define lambda handler
def embed_to_db_similar_handler(event, context):
    # Starting point for response formatting
    result = {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": {"Content-Type": "application/json"},
        "multiValueHeaders": {},
        "body": {"warnings": []}
    }

    # Get input from body or query string
    if ('embed' in event):
        embed_text = event['embed']
    elif ('body' in event and event['body'] != '' and 'embed' in json.loads(event['body'])):
        embed_text = json.loads(event['body'])['embed']
    elif ('queryStringParameters' in event and 'embed' in event['queryStringParameters']):
        embed_text = event['queryStringParameters']['embed']
    else:
        result['statusCode'] = 500
        result['body'] = {'msg': 'Error! Valid input text not provided!'}
        result['headers']['Content-Type'] = "application/json"
        return json.dumps(result)

    # Get "best of" value from body or query string (or <0 for full list)
    best_of = best_of_def
    if ('num' in event):
        best_of = event['num']
    elif ('body' in event and event['body'] != '' and 'num' in json.loads(event['body'])):
        best_of = json.loads(event['body'])['num']
    elif ('queryStringParameters' in event and 'num' in event['queryStringParameters']):
        best_of = event['queryStringParameters']['num']

    # Assign to best of if possible
    try:
        if (best_of != best_of_def):  # if input found (type/value mismatch)
            best_of = int(best_of)
    except ValueError:
        best_of = best_of_def
        result['body']['warnings'].append(
            f'Provided value for "num" invalid, using default of {best_of_def}.')
    if (best_of == 0):
        result['body']['warnings'].append(
            f'Zero results requested with the "num" value of 0. Use value <0 for maximum possible.')

    # Handle unicode in event_text and parse it to a list
    embed: list = literal_eval(unidecode(embed_text))

    # Found event_text, use it and return result
    try:
        res = process_input_list(embed, best_of)
        result['statusCode'] = 200
        result['body']['msg'] = str(res)
        result['headers']['Content-Type'] = "application/json"
        if (res != None and len(res) > 0):
            best_score, best_idx = res[0]
            best_url = f'https://incidentdatabase.ai/apps/discover?display=details&incident_id={best_idx}'
            result['body']['best_url'] = best_url
    except:
        result['statusCode'] = 500
        result['body']['warnings'].append(
            "Error occurred while processing input text!")
        result['headers']['Content-Type'] = "application/json"

    return json.dumps(result)





event_text = ""
incident = 1
with open(f"./tests/unit/testing_materials/lambda_test_request_incident_{incident}.json", "r", encoding="utf-8") as text_json_fp:
    text_json = json.load(text_json_fp)
    text = text_json["text"]
    event_text = unidecode(text[:6000])

embed = get_embedding(event_text)
json_out = {"embed":str(embed.detach().tolist())}

# with open(f"./tests/unit/testing_materials/lambda_test_request_incident_{incident}_embedding.json", "w") as json_file:
#     json.dump(json_out, json_file)

print(compute_cosine_sim_e_e(embed, torch.tensor(literal_eval(json_out["embed"]))))


# with open("tests/unit/testing_materials/lambda_test_request_incident_1_embedding.json", "r") as json_fp:
#     print(embed_to_db_similar_handler(json.load(json_fp), None))
