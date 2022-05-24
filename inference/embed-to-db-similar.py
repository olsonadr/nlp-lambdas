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


def list_files(startpath):
    res = ""
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        res = res + ('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            res = res + ('{}{}'.format(subindent, f))
    return res

# # Get model and tokenizer from EFS or download it to EFS
# model_path = os.path.join(
#     os.environ["TRANSFORMERS_CACHE"], os.environ['MODEL_DIR'], os.environ["MODEL_FILENAME"])
# model_dir = os.path.join(
#     os.environ["TRANSFORMERS_CACHE"], os.environ['MODEL_DIR'])
# hf_uri = os.environ["HF_MODEL_URI"]

# # If it exists in the EFS, load from EFS
# if os.path.isfile(model_path):
#     tokenizer = LongformerTokenizer.from_pretrained(hf_uri)
#     model = LongformerModel.from_pretrained(hf_uri)
#     tokenizer.save_pretrained(model_dir)
#     model.save_pretrained(model_dir)
# # Else, not saved into EFS yet, get from hf and save
# else:
#     tokenizer = LongformerTokenizer.from_pretrained(
#         model_dir, local_files_only=True)
#     model = LongformerModel.from_pretrained(model_dir, local_files_only=True)


# # Constants
# incidents_path = os.path.join(
#     os.environ["TRANSFORMERS_CACHE"], os.environ["INCIDENTS_FILENAME"])
# csv_path = os.path.join(
#     os.environ["TRANSFORMERS_CACHE"], os.environ["CSV_FILENAME"])
model = LongformerModel.from_pretrained(
    '/function/model', local_files_only=True)
tokenizer = LongformerTokenizer.from_pretrained(
    '/function/model', local_files_only=True)
csv_path = '/function/db_state/incidents.csv'
incidents_path = '/function/db_state/state.csv'
best_of_def = 3

# Load in a list of incident states from a CSV
state = pd.read_csv(incidents_path, converters={"mean": literal_eval})

# Get longformer embedding
def get_embedding(text: str):
    inp = tokenizer(text,
                    padding="longest",
                    truncation="longest_first",
                    return_tensors="pt")
    return model(**inp).last_hidden_state[0][0]

# Compute cosine similarity between two tensors
# Returns a single value of the cosine_sim
def compute_cosine_sim_e_e(embed_1: Union[torch.Tensor, list], embed_2: Union[torch.Tensor, list]):
    embed_1 = embed_1 if type(embed_1) == torch.Tensor else torch.tensor(embed_1)
    embed_2 = embed_2 if type(embed_2) == torch.Tensor else torch.tensor(embed_2)
    return torch.nn.functional.cosine_similarity(embed_1, embed_2, dim=-1)

# Compute cosine similarity between a tensor and all embeddings in a db state DataFrame
# Returns a list of tuples (cosine_sim, incident_id) for each incident in dataframe
def compute_cosine_sim_e_df(embed: Union[torch.Tensor, list], dataframe: pd.DataFrame):
    embed = embed if type(embed) == torch.Tensor else torch.tensor(embed)
    return [(
        compute_cosine_sim_e_e(embed, torch.tensor(
            dataframe.loc[i, "mean"])).item(),
        dataframe.loc[i, "incident_id"]
    ) for i in range(len(state))]

# Process input text for text-to-db-similar computation
# Returns a list of the most N (best_of) similar incidents with scores and IDs
def process_input_list(embed: list, best_of: int = best_of_def):
    cosine_sims = sorted(compute_cosine_sim_e_df(embed, state), reverse=True)
    if (best_of >= 0):
        return cosine_sims[:best_of]
    else:
        return cosine_sims

# Old code that above functions replicate
# def test(text):
#     inp = tokenizer(text,
#                     padding="longest",
#                     truncation="longest_first",
#                     return_tensors="pt")
#     out = model(**inp)
#     sims = [(torch.nn.functional.cosine_similarity(
#                  out.last_hidden_state[0][0],
#                  torch.tensor(state.loc[i,"mean"]),
#                  dim=-1).item(),
#              state.loc[i,"incident_id"]) for i in range(len(state))]
#     return sims
#
# def inputted(whole_text, best_of=best_of_def):
#     sims = [j for j in sorted(test(whole_text), reverse=True)]
#     if (best_of >= 0):
#         return sims[:best_of]
#     else:
#         return sims
#
# # What to do to correctly formatted input event_text
# def process(event_text, best_of=best_of_def):
#     # return tokenizer(event_text)
#     return inputted(event_text, best_of)


# Define lambda handler
def handler(event, context):
    # Starting point for response formatting
    result = {
        "isBase64Encoded": False,
        "statusCode": 500,
        "headers": {"Content-Type": "application/json"},
        "multiValueHeaders": {},
        "body": {"warnings": []}
    }

    # Get input from body or query string
    try:
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
    except:
        result['statusCode'] = 500
        result['body'] = {'msg': 'Error! Parsing input gave exception!'}
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

    # Handle unicode in event_text and parse it to a list (removing up to 10 levels of nested quotes, just in case)
    # embed:list = literal_eval(unidecode(embed_text))
    try:
        embed = unidecode(embed_text); count=0; count_max=10
        while type(embed) != list:
            # Check if we've tried too many times and give up if so
            count = count + 1
            if (count > count_max): raise Exception
            # Try to evaluate embed_text to a list literal
            embed:list = literal_eval(embed)
    except:
        result['statusCode'] = 500
        result['body'] = {'msg': 'Error during literal evaluation of embed_text!'}
        result['headers']['Content-Type'] = "application/json"
        return json.dumps(result)

    # Found event_text, use it and return result
    try:
        print(type(embed))
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
        result['body'] = {'msg': 'Error occurred while processing input text!'}
        result['headers']['Content-Type'] = "application/json"
        
    return json.dumps(result)

    # # Python 3.10 required for this nicer match formatting (not updated w/ proxy integration)
    # # Get input from body or query string
    # match event:
    #     # If an expected format
    #     case {'text': event_text} \
    #             | {'body': {'text': event_text}} \
    #             | {'queryStringParameters': {'text': event_text}}:
    #         result['statusCode'] = 200
    #         # result['body'] = nlp(event_text)[0]
    #         result['body'] = inputted(event_text)
    #         result['headers']['Content-Type'] = "application/json"
    #         return result
    #     # Else if input not given, return error
    #     case _:
    #         result['statusCode'] = 500
    #         result['body'] = "Error! Valid input text not provided!"
    #         result['headers']['Content-Type'] = "application/json"
    #         return result

