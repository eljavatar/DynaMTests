import json
import copy
import os
import pandas as pd
import re

from pathlib import Path
from pprint import pprint
from tqdm import tqdm
from ParserUtils import ParserUtils
# from datasets import load_dataset
# from transformers import AutoTokenizer, T5Config



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


def get_focal_methods_by_d4j_project(parser_utils: ParserUtils, 
                                     path_d4j_dataset: str, 
                                     input_encoding: str,
                                     findings_by_d4j_project: dict[str, dict[str, set[str]]]):
    all_list_paths_focal_class: set[str] = set()
    focal_class_paths_by_d4j_project: dict[str, set[str]] = {}
    focal_methods_by_d4j_project: dict[str, set[str]] = {}
    focal_methods_findigs: dict[str, dict[str, set[str]]] = {}

    # list_projects_d4j = ['Csv', 'Cli', 'Lang', 'Chart', 'Gson']
    # list_projects_d4j = ['Closure', 'Cli', 'Codec', 'Collections', 'Compress', 'Csv', 'JxPath', 'Lang', 'Math', 'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Chart', 'Time', 'Jsoup', 'Mockito']
    list_projects_d4j = ["Cli", "Compress", "JacksonCore", "JacksonDatabind"]
    
    for d4j_project in tqdm(list_projects_d4j, desc="Extrayendo metadata de d4j_dataset"):
        path_d4j_project_dataset = os.path.join(path_d4j_dataset, d4j_project)

        findings_by_path_focal_class = findings_by_d4j_project[d4j_project]

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
                    
                    path_focal_class = method_data_d4j['focal_class']['file'].strip()
                    path_focal_class = clean_tabs_and_new_lines(path_focal_class)

                    focal_method_body = method_data_d4j['focal_method']['body']
                    focal_method_body = clean_comments_in_code(parser_utils, focal_method_body)
                    focal_method_body = focal_method_body.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")

                    all_list_paths_focal_class.add(path_focal_class)
                    focal_class_paths.add(path_focal_class)
                    focal_methods.add(focal_method_body)

                    if path_focal_class not in findings_by_path_focal_class:
                        continue

                    methods_findings = findings_by_path_focal_class[path_focal_class]
                    
                    if focal_method_body in methods_findings:
                        if d4j_project in focal_methods_findigs:
                            if version_folder in focal_methods_findigs[d4j_project]:
                                focal_methods_findigs[d4j_project][version_folder].add(method_folder)
                            else:
                                focal_methods_findigs[d4j_project][version_folder] = set([method_folder])
                        else:
                            focal_methods_findigs[d4j_project] = {
                                version_folder: set([method_folder])
                                # version_folder: {method_folder}
                            }
                            # focal_methods_findigs[d4j_project][version_folder] = set([method_folder])

                # path_focal_class_txt_file = os.path.join(path_method_folder, 'path_focal_class.txt')
                # if os.path.exists(path_focal_class_txt_file):
                #     with open(path_focal_class_txt_file, mode="r", encoding=input_encoding) as f:
                #         path_focal_class = f.read().strip()
                    
                #     path_focal_class = clean_tabs_and_new_lines(path_focal_class)
                #     focal_class_paths.add(path_focal_class)
        

        focal_class_paths_by_d4j_project[d4j_project] = focal_class_paths
        focal_methods_by_d4j_project[d4j_project] = focal_methods

    return focal_methods_findigs, all_list_paths_focal_class, focal_class_paths_by_d4j_project, focal_methods_by_d4j_project


def export_results_json(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        data_json = json.dumps(data, indent = 4)
        f.write(data_json)



input_encoding = 'utf-8'
validate_against_d4j_dataset = True
d4j_dataset = '/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version'
parser_utils = ParserUtils(input_encoding)


findings_by_d4j_project: dict[str, dict[str, set[str]]] = {}

list_finding_projects = ["Cli", "Compress", "JacksonCore", "JacksonDatabind"]
path_findings_GithubCode = "/CodeParrot_GithubCode"
for finding_project in list_finding_projects:
    path_finfing_project_json_file = os.path.join(path_findings_GithubCode, finding_project + ".json")
    if os.path.exists(path_finfing_project_json_file):
        with open(path_finfing_project_json_file, encoding=input_encoding) as f:
            list_finding_data = json.load(f)
        
        for finding_data in list_finding_data:
            if finding_project in findings_by_d4j_project:
                if finding_data["path"] in findings_by_d4j_project[finding_project]:
                    findings_by_d4j_project[finding_project][finding_data["path"]].add(finding_data["focal_method_existing_in_d4j"])
                else:
                    findings_by_d4j_project[finding_project][finding_data["path"]] = set([finding_data["focal_method_existing_in_d4j"]])
            else:
                findings_by_d4j_project[finding_project] = {
                    finding_data["path"]: set([finding_data["focal_method_existing_in_d4j"]])
                    # finding_data["path"]: {finding_data["focal_method_existing_in_d4j"]}
                }
                # findings_by_d4j_project[finding_project][finding_data["path"]] = set([finding_data["focal_method_existing_in_d4j"]])


focal_methods_findigs, all_list_paths_focal_class, focal_class_paths_by_d4j_project, focal_methods_by_d4j_project = get_focal_methods_by_d4j_project(
    parser_utils, d4j_dataset, input_encoding, findings_by_d4j_project
)
print("\n")
print(f"Total de clases focales: {len(all_list_paths_focal_class)}\n\n")

print("\nCount methods from repos existing in focal_methods_findigs:")
for project, methods_by_version in focal_methods_findigs.items():
    print(f"\n\nProject: {project}. Versions =>")
    for version, methods in methods_by_version.items():
        print(f"Version: {version}. Methods => {methods}")

