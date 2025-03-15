import json
import copy
import os
import pandas as pd
import re

from pathlib import Path
from pprint import pprint
from tqdm import tqdm
from ParserUtils import ParserUtils
from datasets import load_dataset
from transformers import AutoTokenizer, T5Config



pd.set_option('max_colwidth', 300)


DEFECTS4J_PROJECTS_BY_REPO_ID = {
    "Closure": "google/closure-compiler",
    "Cli": "apache/commons-cli",
    "Codec": "apache/commons-codec",
    "Collections": "apache/commons-collections",
    "Compress": "apache/commons-compress",
    "Csv": "apache/commons-csv",
    "JxPath": "apache/commons-jxpath",
    "Lang": "apache/commons-lang",
    "Math": "apache/commons-math",
    "Gson": "google/gson",
    "JacksonCore": "FasterXML/jackson-core",
    "JacksonDatabind": "FasterXML/jackson-databind",
    "JacksonXml": "FasterXML/jackson-dataformat-xml",
    "Chart": "jfree/jfreechart",
    "Time": "JodaOrg/joda-time",
    "JSoup": "jhy/jsoup",
    "Mockito": "mockito/mockito"
}


def clean_tabs_and_new_lines(code: str) -> str:
    # Reemplaza los caracteres de nueva línea y tabulaciones por un espacio
    src_clean = re.sub(r'[\n\t]+', ' ', code)
    # Reemplaza múltiples espacios por un solo espacio
    src_clean = re.sub(r'\s{2,}', ' ', src_clean)
    return src_clean.strip()


def clean_comments_in_code(parser_utils: ParserUtils, body_src: str) -> str:
    modified_code = parser_utils.clean_comments(body_src)
    # Reemplaza los caracteres de nueva línea y tabulaciones por un espacio
    return clean_tabs_and_new_lines(modified_code).strip()


def get_focal_methods_by_d4j_project(parser_utils: ParserUtils, path_d4j_dataset: str, input_encoding: str):
    all_list_paths_focal_class: set[str] = set()
    focal_class_paths_by_d4j_project: dict[str, set[str]] = {}
    focal_methods_by_d4j_project: dict[str, set[str]] = {}

    # list_projects_d4j = ['Csv', 'Cli', 'Lang', 'Chart', 'Gson']
    list_projects_d4j = ['Closure', 'Cli', 'Codec', 'Collections', 'Compress', 'Csv', 'JxPath', 'Lang', 'Math', 'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Chart', 'Time', 'Jsoup', 'Mockito']
    
    for d4j_project in tqdm(list_projects_d4j, desc="Extrayendo metadata de d4j_dataset"):
        path_d4j_project_dataset = os.path.join(path_d4j_dataset, d4j_project)

        focal_methods = set()
        focal_class_paths = set()

        for version_folder in os.listdir(path_d4j_project_dataset):
            path_version_folder = os.path.join(path_d4j_project_dataset, version_folder)
            path_version_folder_methods = os.path.join(path_version_folder, 'methods')

            for method_folder in os.listdir(path_version_folder_methods):
                path_method_folder = os.path.join(path_version_folder_methods, method_folder)
                
                metadata_json_file = os.path.join(path_method_folder, 'metadata.json')
                if os.path.exists(metadata_json_file):
                    with open(metadata_json_file, encoding=input_encoding) as f:
                        method_data_d4j = json.load(f)
                    
                    focal_method_body = method_data_d4j['focal_method']['body']
                    focal_method_body = clean_comments_in_code(parser_utils, focal_method_body)
                    focal_method_body = focal_method_body.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")
                    focal_methods.add(focal_method_body)

                    path_focal_class = method_data_d4j['focal_class']['file'].strip()
                    path_focal_class = clean_tabs_and_new_lines(path_focal_class)
                    focal_class_paths.add(path_focal_class)
                    all_list_paths_focal_class.add(path_focal_class)

                # path_focal_class_txt_file = os.path.join(path_method_folder, 'path_focal_class.txt')
                # if os.path.exists(path_focal_class_txt_file):
                #     with open(path_focal_class_txt_file, mode="r", encoding=input_encoding) as f:
                #         path_focal_class = f.read().strip()
                    
                #     path_focal_class = clean_tabs_and_new_lines(path_focal_class)
                #     focal_class_paths.add(path_focal_class)
        

        focal_class_paths_by_d4j_project[d4j_project] = focal_class_paths
        focal_methods_by_d4j_project[d4j_project] = focal_methods

    return all_list_paths_focal_class, focal_class_paths_by_d4j_project, focal_methods_by_d4j_project


def export_results_json(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        data_json = json.dumps(data, indent = 4)
        f.write(data_json)


print("\nLoading Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("Salesforce/codet5p-220m", cache_dir="/huggingface_models/")


# Si existen en CodeSearchNet, no van a existir en el conjunto de entrenamiento 
# /root/.ir_datasets/downloads/c0288db91f067c95bb952577949e7b13
print("\nLoading CodeSerachNet dataset...")
docs_codesearchnet = load_dataset('irds/codesearchnet', 'docs', cache_dir='/CodeSearchNet/dataset')
print("Aplicando filtro a CodeSearchNet...")
java_docs_codesearchnet = docs_codesearchnet.filter(lambda example: example["language"] == "java")
print("\n")

# docs_train = load_dataset('irds/codesearchnet_train', 'docs', cache_dir='/CodeSearchNet/dataset')

transpose_d4j_repos: dict[str, str] = {}
for key, value in DEFECTS4J_PROJECTS_BY_REPO_ID.items():
    transpose_d4j_repos[value.lower()] = key


input_encoding = 'utf-8'
validate_against_d4j_dataset = True
d4j_dataset = '/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version'
parser_utils = ParserUtils(input_encoding)

list_repos_codesearchnet = set()
list_repos_d4j_existing_in_codesearchnet = set()


all_list_paths_focal_class, focal_class_paths_by_d4j_project, focal_methods_by_d4j_project = get_focal_methods_by_d4j_project(parser_utils, d4j_dataset, input_encoding)
print("\n")
print(f"Total de clases focales: {len(all_list_paths_focal_class)}\n\n")


d4j_methods_existing_in_codesearch_net_validating_match: dict[str, set[str]] = {}
d4j_methods_existing_in_codesearch_net_validating_repo: dict[str, int] = {}

counts_java = 0
# for record in tqdm(docs_codesearchnet, desc="Analyzing CodeSearchNet"):
for record in tqdm(java_docs_codesearchnet, desc="Analyzing CodeSearchNet"):
    if record['language'] != 'java':
        continue

    repo_codesearchnet = record['repo'].lower()

    counts_java += 1
    list_repos_codesearchnet.add(repo_codesearchnet)

    if repo_codesearchnet in transpose_d4j_repos:
        list_repos_d4j_existing_in_codesearchnet.add(repo_codesearchnet)
        d4j_project = transpose_d4j_repos[repo_codesearchnet]
        if d4j_project in d4j_methods_existing_in_codesearch_net_validating_repo:
            d4j_methods_existing_in_codesearch_net_validating_repo[d4j_project] += 1
        else:
            d4j_methods_existing_in_codesearch_net_validating_repo[d4j_project] = 1
        
        continue

    # code_from_codesearchnet = record['code']
    # code_from_codesearchnet = clean_comments_in_code(parser_utils, code_from_codesearchnet)
    # code_from_codesearchnet = code_from_codesearchnet.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")

    # exists_in_d4j_dataset = False
    # for d4j_project, focal_methods in focal_methods_by_d4j_project.items():
    #     if code_from_codesearchnet in focal_methods:
    #         exists_in_d4j_dataset = True
    #         if d4j_project in d4j_methods_existing_in_codesearch_net_validating_match:
    #             # d4j_existing_in_codesearch_net[d4j_project] += 1
    #             d4j_methods_existing_in_codesearch_net_validating_match[d4j_project].add(code_from_codesearchnet)
    #         else:
    #             # d4j_existing_in_codesearch_net[d4j_project] = 1
    #             d4j_methods_existing_in_codesearch_net_validating_match[d4j_project] = set()
    #             d4j_methods_existing_in_codesearch_net_validating_match[d4j_project].add(code_from_codesearchnet)

    # for key, value in DEFECTS4J_PROJECTS_BY_REPO_ID.items():
    #     if value.lower() == record['repo'].lower():
    #         if key in d4j_repos_existing_in_codesearch_net:
    #             d4j_repos_existing_in_codesearch_net[key] += 1
    #         else:
    #             d4j_repos_existing_in_codesearch_net[key] = 1
        
    #         break


print(f"\n\nTotal inputs java in CodeSearchNet: {counts_java}")

print("\nCount methods from repos existing in CodeSearchNet:")
for key, value in d4j_methods_existing_in_codesearch_net_validating_repo.items():
    print(f"{key}: {value}")

# print("\n")
# print("\nCount methods existing in CodeSearchNet:")
# for key, value in d4j_methods_existing_in_codesearch_net_validating_match.items():
#     print(f"{key}: {len(value)}")

print("\n\n")

# print(transpose_d4j_repos)
# print("\n")


print("Loading CodeT5+ dataset (codeparrot/github-code)...")
ds_githubcode = load_dataset(
    "codeparrot/github-code", 
    cache_dir='/CodeParrot_GithubCode/dataset', 
    # trust_remote_code=True, 
    streaming=True, 
    split="train", 
    # languages=["Dockerfile"]
    # licenses=["mit", "isc", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "cc0-1.0", "unlicense"],
    
    # 
)
# print(next(iter(ds_githubcode)))

# En CodeT5+ no tuvieron en cuenta los files pertenecientes a repositorios existentes en CodeSearchNet
print("Aplicando filtro a codeparrot/github-code...")
java_ds_codet5plus = ds_githubcode.filter(
    lambda example: 
        example["language"] == "Java" 
        and example["license"] in ["mit", "isc", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "cc0-1.0", "unlicense"]
        # and example["repo_name"].lower() not in list_repos_codesearchnet
        and example["repo_name"].lower() not in list_repos_d4j_existing_in_codesearchnet
        and example["repo_name"].lower() in transpose_d4j_repos
        and example["path"] in all_list_paths_focal_class
)
# print(next(iter(java_ds_codet5plus)))
# print("")
# print(next(iter(java_ds_codet5plus)))
# print("")
# print(next(iter(java_ds_codet5plus)))

print("\n")

d4j_methods_existing_in_ds_codet5plus_validating_repo: dict[str, list] = {}
count_analyzed = 0

for item in tqdm(java_ds_codet5plus, desc="Analyzing codeparrot/github-code"):
    d4j_project = transpose_d4j_repos[item['repo_name'].lower()]
    # print(f"\nD4J Project: {d4j_project}\n")

    # item_path = item['path']
    # print(f"\nItem path: {item_path}\n")

    # list_path_focal_classes: set[str] = focal_class_paths_by_d4j_project[d4j_project]
    # print("")
    # print(list_path_focal_classes)
    # print("")

    # print("\nValidando si path existe...")
    # if not (item_path in list_path_focal_classes):
    #     # Omitimos si no es una clase focal
    #     print("\nNo existe path")
    #     continue
    # print("\nSi existe path")

    item_code = item['code']

    tokenized_input = tokenizer(item_code, return_attention_mask=False, add_special_tokens=False)
    input_length = len(tokenized_input['input_ids'])
    if input_length < 50 or input_length > 2000:
        # En CodeT5+ solo tomaron files con longitud de entre 50 y 2000 tokens
        # Si está por fuera de ese rango, no lo tenemos en cuenta
        continue

    count_analyzed += 1

    new_item = copy.deepcopy(item)

    code_from_codet5plus_dataset = new_item['code']
    code_from_codet5plus_dataset = clean_comments_in_code(parser_utils, code_from_codet5plus_dataset)
    code_from_codet5plus_dataset = code_from_codet5plus_dataset.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")

    new_item['code'] = code_from_codet5plus_dataset


    list_body_methods: set[str] = parser_utils.get_body_methods_from_class(code_from_codet5plus_dataset)
    # print("")
    # print(list_body_methods)
    # print("")


    list_focal_methods = focal_methods_by_d4j_project[d4j_project]

    exists_in_d4j_dataset = False
    for body_method in list_body_methods:
        if body_method in list_focal_methods:
            exists_in_d4j_dataset = True
            item_with_existing_focal_method = copy.deepcopy(new_item)
            item_with_existing_focal_method['focal_method_existing_in_d4j'] = body_method
            
            if d4j_project in d4j_methods_existing_in_codesearch_net_validating_match:
                d4j_methods_existing_in_ds_codet5plus_validating_repo[d4j_project].append(item_with_existing_focal_method)
            else:
                d4j_methods_existing_in_ds_codet5plus_validating_repo[d4j_project] = [item_with_existing_focal_method]
    
    # if exists_in_d4j_dataset:
    #     break

    # if d4j_project in d4j_methods_existing_in_ds_codet5plus_validating_repo:
    #     d4j_methods_existing_in_ds_codet5plus_validating_repo[d4j_project].append(new_item)
    # else:
    #     d4j_methods_existing_in_ds_codet5plus_validating_repo[d4j_project] = [new_item]
    
    # break
    


print(f"\n\nTotal analyzed inputs java in codeparrot/github-code: {count_analyzed}")

print("\nSaving files from repos existing in CodeT5+ dataset:")
for key, value in d4j_methods_existing_in_ds_codet5plus_validating_repo.items():
    print(f"{key}: {len(value)}")

    path_file_json = os.path.join("/CodeParrot_GithubCode", f"{key}.json")

    export_results_json(value, path_file_json)

print("\n")
    

