import argparse
import copy
import json
import os
import re
import shutil
import time
from tqdm import tqdm
from ParserUtils import ParserUtils


def get_total_repos(path: str):
    count_repos = 0

    # Recorre los elementos en el directorio actual
    #for elemento in os.listdir('.'):
    for elemento in os.listdir(path):
        path_elemento = os.path.join(path, elemento)
        # Verifica si el elemento es una carpeta
        if os.path.isdir(path_elemento):
            #print("elemento es folder: " + elemento)
            count_repos += 1
    
    return count_repos


"""
corpus
    - data_by_project_and_version
        - Gson
            - 1 (version)
                - focal_classes
                    - FocalClass1.java
                    - FocalClass2.java
                - methods
                    - 0 (each method)
                        - all_metadata.json
                        - src_fm_fc_ms_ff.txt
                        - src_fm_fc_dctx.txt
                        - src_fm_fc_dctx_priv.txt
                        - imports_focal_class.txt
                        - path_focal_class.txt
                    - 1
                    - 2
            - 2
            - 3
        - Csv
        - Lang
        - Cli
        - Chart
    - json
        - Gson
            - Gson_1_f
                - Gson_1_f_0.json
                - Gson_1_f_1.json
                - Gson_1_f_2.json
            - Gson_2_f
            - Gson_3_f
        - Csv
            - Csv_1_f
            - Csv_2_f
            - Csv_3_f
        - Lang
        - Cli
        - Chart
    - raw
        - Gson
            - src_fm_fc_ms_ff.txt
            - src_fm_fc_dctx.txt
            - src_fm_fc_dctx_priv.txt
            - imports_focal_class.txt
            - path_focal_class.txt
        - Csv
        - Lang
        - Cli
        - Chart

"""


def build_corpus(input_dataset: str,
                 input_encoding: str,
                 project_id: str,
                 list_paths_by_project_id: list[str],
                 output_corpus: str,
                 tag_focal_context_start: str,
                 tag_focal_context_end: str,
                 tag_external_context_start: str,
                 tag_external_context_end: str,
                 tag_private_focal_context_start: str,
                 tag_private_focal_context_end: str):
    
    parser_utils = ParserUtils(input_encoding)
    
    #total_repos = get_total_repos(input_dataset)
    total_repos = len(list_paths_by_project_id)
    print(f"\n\nTotal repos: {str(total_repos)}")

    path_out_corpus_data = os.path.join(output_corpus, "data_by_project_and_version/" + project_id)
    os.makedirs(path_out_corpus_data, exist_ok=True)

    path_out_corpus_json = os.path.join(output_corpus, "json/" + project_id)
    os.makedirs(path_out_corpus_json, exist_ok=True)
    
    path_out_corpus_raw = os.path.join(output_corpus, "raw/" + project_id)
    os.makedirs(path_out_corpus_raw, exist_ok=True)

    list_src_fm_fc_ms_ff = []
    list_src_fm_fc_dctx = []
    list_src_fm_fc_dctx_priv = []
    list_imports_focal_class = []
    list_package_focal_class = []
    list_path_focal_class = []
    
    index_repo = 1

    # project_name_version = os.path.split(project_path)[1]
    #x = repo_path
    #for repo_folder in next(os.walk(input_dataset))[1]:
    for project_path in list_paths_by_project_id:
        project_name_version = os.path.split(project_path)[1]
        version = project_name_version.split("_")[1] # Gson_1_f

        path_project_and_version = os.path.join(path_out_corpus_data, str(version))
        os.makedirs(path_project_and_version, exist_ok=True)

        path_project_and_version_focal_classes = os.path.join(path_project_and_version, "focal_classes")
        path_project_and_version_methods = os.path.join(path_project_and_version, "methods")

        os.makedirs(path_project_and_version_focal_classes, exist_ok=True)
        os.makedirs(path_project_and_version_methods, exist_ok=True)

        # Copy focal classes
        path_focal_classes_source = os.path.join(project_path, "focal_classes")
        if os.path.exists(path_focal_classes_source):
            classes_to_copy = os.listdir(path_focal_classes_source)
            for class_to_copy in classes_to_copy:
                shutil.copy(os.path.join(path_focal_classes_source, class_to_copy), path_project_and_version_focal_classes)

        #path_dataset_repo = os.path.join(input_dataset, repo_folder)
        path_corpus_repo = os.path.join(path_out_corpus_json, project_name_version)
        os.makedirs(path_corpus_repo, exist_ok=True)
        i = 0

        message = f"Building json corpus repository {project_name_version} - (Nro. repo: {str(index_repo)} of {str(total_repos)})"
        for file in tqdm(os.listdir(project_path), desc=message):
            if file.endswith('.json'):
                path_json_file_method_dataset = os.path.join(project_path, file)

                with open(path_json_file_method_dataset, encoding=input_encoding) as f:
                    data = json.load(f)

                    src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_focal_class, package_focal_class, path_focal_class = extract_data_from_mapped_test_case(
                        parser_utils,
                        data, 
                        tag_focal_context_start, 
                        tag_focal_context_end, 
                        tag_external_context_start, 
                        tag_external_context_end,
                        tag_private_focal_context_start,
                        tag_private_focal_context_end, file)

                #file_without_extension = file.split('.')[0]
                #file_corpus_json = file_without_extension + "_corpus.json"
                file_corpus_json = project_name_version + "_" + str(i) + "_corpus.json"
                path_file_corpus_json = os.path.join(path_corpus_repo, file_corpus_json)

                data_json = {
                    'src_fm_fc_ms_ff': src_fm_fc_ms_ff,
                    'src_fm_fc_dctx': src_fm_fc_dctx,
                    'src_fm_fc_dctx_priv': src_fm_fc_dctx_priv,
                    'imports_focal_class': imports_focal_class,
                    'package_focal_class': package_focal_class,
                    'path_focal_class': path_focal_class
                }
                
                export_corpus_json(data_json, path_file_corpus_json)

                path_data_method = os.path.join(path_project_and_version_methods, str(i))
                os.makedirs(path_data_method, exist_ok=True)

                export_corpus_json(data_json, os.path.join(path_data_method, "corpus.json"))
                export_corpus_txt(src_fm_fc_ms_ff, os.path.join(path_data_method, "src_fm_fc_ms_ff.txt"))
                export_corpus_txt(src_fm_fc_dctx, os.path.join(path_data_method, "src_fm_fc_dctx.txt"))
                export_corpus_txt(src_fm_fc_dctx_priv, os.path.join(path_data_method, "src_fm_fc_dctx_priv.txt"))
                export_corpus_txt(imports_focal_class, os.path.join(path_data_method, "imports_focal_class.txt"))
                export_corpus_txt(package_focal_class, os.path.join(path_data_method, "package_focal_class.txt"))
                export_corpus_txt(path_focal_class, os.path.join(path_data_method, "path_focal_class.txt"))

                list_src_fm_fc_ms_ff.append(src_fm_fc_ms_ff)
                list_src_fm_fc_dctx.append(src_fm_fc_dctx)
                list_src_fm_fc_dctx_priv.append(src_fm_fc_dctx_priv)
                list_imports_focal_class.append(imports_focal_class)
                list_package_focal_class.append(package_focal_class)
                list_path_focal_class.append(path_focal_class)

                # Copy method metadata
                shutil.copy(path_json_file_method_dataset, os.path.join(path_data_method, "metadata.json"))

                i += 1

        index_repo += 1
    
    
    print("\nExporting raw corpus")
    export_corpus_raw(
        path_out_corpus_raw, 
        list_src_fm_fc_ms_ff,
        list_src_fm_fc_dctx,
        list_src_fm_fc_dctx_priv,
        list_imports_focal_class,
        list_package_focal_class,
        list_path_focal_class,
        "Writing raw corpus"
    )

    print(f"\nTotal corpus {project_id}: {str(len(list_src_fm_fc_ms_ff))}\n")


def export_corpus_json(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        data_json = json.dumps(data)
        f.write(data_json)


def export_corpus_txt(text: str, file_path: str):
    """
    Exports data as txt file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text + "\n")


def export_corpus_raw(path_out_courpus_raw: str, 
                      list_src_fm_fc_ms_ff: list[str],
                      list_src_fm_fc_dctx: list[str],
                      list_src_fm_fc_dctx_priv: list[str],
                      list_imports_focal_class: list[str],
                      list_package_focal_class: list[str],
                      list_path_focal_class: list[str],
                      msg_tqdm: str):
    
    path_file_src_fm_fc_ms_ff = os.path.join(path_out_courpus_raw, "src_fm_fc_ms_ff.txt")
    path_file_src_fm_fc_dctx = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx.txt")
    path_file_src_fm_fc_dctx_priv = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx_priv.txt")
    path_file_imports_focal_class = os.path.join(path_out_courpus_raw, "imports_focal_class.txt")
    path_file_package_focal_class = os.path.join(path_out_courpus_raw, "package_focal_class.txt")
    path_file_path_focal_class = os.path.join(path_out_courpus_raw, "path_focal_class.txt")

    #Removing older version of the file outputs
    if os.path.exists(path_file_src_fm_fc_ms_ff):
        os.remove(path_file_src_fm_fc_ms_ff)

    if os.path.exists(path_file_src_fm_fc_dctx):
        os.remove(path_file_src_fm_fc_dctx)

    if os.path.exists(path_file_src_fm_fc_dctx_priv):
        os.remove(path_file_src_fm_fc_dctx_priv)

    if os.path.exists(path_file_imports_focal_class):
        os.remove(path_file_imports_focal_class)

    if os.path.exists(path_file_package_focal_class):
        os.remove(path_file_package_focal_class)
    
    if os.path.exists(path_file_path_focal_class):
        os.remove(path_file_path_focal_class)

    #Writing to file
    with (
            open(path_file_src_fm_fc_ms_ff, 'w', encoding='utf-8') as f_src_fm_fc_ms_ff, 
            open(path_file_src_fm_fc_dctx, 'w', encoding='utf-8') as f_src_fm_fc_dctx, 
            open(path_file_src_fm_fc_dctx_priv, 'w', encoding='utf-8') as f_src_fm_fc_dctx_priv, 
            open(path_file_imports_focal_class, 'w', encoding='utf-8') as f_imp_f,
            open(path_file_package_focal_class, 'w', encoding='utf-8') as f_pack_fc,
            open(path_file_path_focal_class, 'w', encoding='utf-8') as f_path_fc
        ):
        for index in tqdm(range(len(list_src_fm_fc_ms_ff)), desc=msg_tqdm):
            f_src_fm_fc_ms_ff.write(list_src_fm_fc_ms_ff[index] + "\n")
            f_src_fm_fc_dctx.write(list_src_fm_fc_dctx[index] + "\n")
            f_src_fm_fc_dctx_priv.write(list_src_fm_fc_dctx_priv[index] + "\n")
            f_imp_f.write(list_imports_focal_class[index] + "\n")
            f_pack_fc.write(list_package_focal_class[index] + "\n")
            f_path_fc.write(list_path_focal_class[index] + "\n")


def extract_data_from_mapped_test_case(parser_utils: ParserUtils,
                                       data: dict,
                                       tag_focal_context_start: str,
                                       tag_focal_context_end: str,
                                       tag_external_context_start: str,
                                       tag_external_context_end: str,
                                       tag_private_focal_context_start: str,
                                       tag_private_focal_context_end: str, file):
    focal_class = data['focal_class']
    focal_method = data['focal_method']
    path_focal_class = focal_class['file']
    package_focal_class = focal_class['package']

    src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv = build_format_corpus(
        parser_utils,
        focal_class, 
        focal_method, 
        tag_focal_context_start, 
        tag_focal_context_end, 
        tag_external_context_start, 
        tag_external_context_end,
        tag_private_focal_context_start,
        tag_private_focal_context_end
    )

    imports_focal_class = clean_tabs_and_new_lines('|'.join(focal_class['imports']))
    imports_focal_class = imports_focal_class.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    return src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_focal_class, package_focal_class, path_focal_class


def build_format_corpus(parser_utils: ParserUtils,
                        focal_class: dict,
                        focal_method: dict,
                        tag_focal_context_start: str,
                        tag_focal_context_end: str,
                        tag_external_context_start: str,
                        tag_external_context_end: str,
                        tag_private_focal_context_start: str,
                        tag_private_focal_context_end: str):
    
    format_class_signature = '{} {} {}'
    class_signature = format_class_signature.format(focal_class['class_name'], focal_class['superclass'], focal_class['interfaces']).strip()
    class_signature = clean_comments_in_code(parser_utils, class_signature)
    
    body_method = clean_comments_in_code(parser_utils, focal_method['body'])
    body_method = body_method.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    focal_class_methods = focal_class['methods']
    focal_class_fields = focal_class['fields']

    constructors = [meth['full_signature_parameters'] + ";" for meth in focal_class_methods if meth['is_constructor'] == True]
    constructors_str = '\n'.join(constructors)
    constructors_str = clean_comments_in_code(parser_utils, constructors_str)

    non_private_methods = [meth['full_signature_parameters'] + ";" for meth in focal_class_methods if meth['is_constructor'] == False and 'private' not in meth['modifiers']]
    non_private_methods_str = '\n'.join(non_private_methods)
    non_private_methods_str = clean_comments_in_code(parser_utils, non_private_methods_str)

    non_private_fields = [field['original_string'] for field in focal_class_fields if 'private' not in field['modifier']]
    non_private_fields_str = '\n'.join(non_private_fields)
    non_private_fields_str = clean_comments_in_code(parser_utils, non_private_fields_str)


    format_src_fm_fc_ms_ff = '{} {{ {} {} {} {} }}'
    src_fm_fc_ms_ff = format_src_fm_fc_ms_ff.format(
        class_signature, 
        body_method, 
        constructors_str, 
        non_private_methods_str, 
        non_private_fields_str
    )
    src_fm_fc_ms_ff = clean_tabs_and_new_lines(src_fm_fc_ms_ff)


    used_private_signatures_of_class = [meth['full_signature_parameters'] + ";" for meth in focal_class_methods if 'private' in meth['modifiers'] and meth['is_constructor'] == True]
    used_private_signatures_of_class.extend([meth['full_signature_parameters'] + ";" for meth in focal_method['class_private_deps_used']['methods'] if 'private' in meth['modifiers'] and meth['is_constructor'] == False])
    used_private_signatures_of_class.extend([field['original_string'] for field in focal_method['class_private_deps_used']['fields'] if 'private' in field['modifier']])
    used_private_signatures_of_class_str = '\n'.join(used_private_signatures_of_class)
    used_private_signatures_of_class_str = clean_comments_in_code(parser_utils, used_private_signatures_of_class_str)

    used_non_private_signatures_of_class = [meth['full_signature_parameters'] + ";" for meth in focal_class_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == True]
    used_non_private_signatures_of_class.extend([meth['full_signature_parameters'] + ";" for meth in focal_method['class_private_deps_used']['methods'] if 'private' not in meth['modifiers'] and meth['is_constructor'] == False])
    used_non_private_signatures_of_class.extend([field['original_string'] for field in focal_method['class_private_deps_used']['fields'] if 'private' not in field['modifier']])
    used_non_private_signatures_of_class_str = '\n'.join(used_non_private_signatures_of_class)
    used_non_private_signatures_of_class_str = clean_comments_in_code(parser_utils, used_non_private_signatures_of_class_str)

    signatures_of_external_dependencies = focal_method['signatures_of_external_dependencies']
    
    external_context = []
    for ext_class_sig in signatures_of_external_dependencies:
        signatures_by_ext_class = signatures_of_external_dependencies[ext_class_sig]
        ext_class_sig_cleaned = clean_comments_in_code(parser_utils, ext_class_sig)
        signatures_by_ext_class_str = '\n'.join(signatures_by_ext_class)
        signatures_by_ext_class_str = clean_comments_in_code(parser_utils, signatures_by_ext_class_str)
        
        format_src_ext_class = '{} {{ {} }}'
        src_ext_class = format_src_ext_class.format(ext_class_sig_cleaned, signatures_by_ext_class_str)
        #src_ext_class = clean_comments_in_code(parser_utils, src_ext_class)
        external_context.append(src_ext_class)
    
    external_context_str = '\n'.join(external_context).strip()
    external_context_str = clean_comments_in_code(parser_utils, external_context_str)
    src_external_context = tag_external_context_start + external_context_str + tag_external_context_end


    format_src_fm_fc_dctx = '{}{} {{ {} {} {} }}{} {}'
    src_fm_fc_dctx = format_src_fm_fc_dctx.format(
        tag_focal_context_start, 
        class_signature, 
        body_method, 
        used_non_private_signatures_of_class_str, 
        used_private_signatures_of_class_str, 
        tag_focal_context_end, 
        src_external_context
    )
    src_fm_fc_dctx = clean_tabs_and_new_lines(src_fm_fc_dctx)


    format_src_fm_fc_dctx_priv = '{}{} {{ {} {} {} }}{} {}'
    src_fm_fc_dctx_priv = format_src_fm_fc_dctx_priv.format(
        tag_focal_context_start,
        class_signature, 
        body_method, 
        used_non_private_signatures_of_class_str, 
        tag_private_focal_context_start + used_private_signatures_of_class_str + tag_private_focal_context_end, 
        tag_focal_context_end, 
        src_external_context
    )
    src_fm_fc_dctx_priv = clean_tabs_and_new_lines(src_fm_fc_dctx_priv).strip()

    return src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv


def clean_comments_in_code(parser_utils: ParserUtils, body_src: str) -> str:
    modified_code = parser_utils.clean_comments(body_src)
    # Reemplaza los caracteres de nueva línea y tabulaciones por un espacio
    return clean_tabs_and_new_lines(modified_code).strip()


def clean_tabs_and_new_lines(code: str) -> str:
    # Reemplaza los caracteres de nueva línea y tabulaciones por un espacio
    src_clean = re.sub(r'[\n\t]+', ' ', code)
    # Reemplaza múltiples espacios por un solo espacio
    src_clean = re.sub(r'\s{2,}', ' ', src_clean)
    return src_clean.strip()


def parse_args():
    """
    Parse the args passed from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dataset", 
        type=str, 
        default="E:/000_Tesis/custom_scripts_d4j/output_fc_only_public",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--input_encoding", 
        type=str, 
        default="cp1252",
        #default="utf-8",
        help="Encoding of the inputs json files (It depends on the OS where the dataset was built: Windows=cp1252, Unix/Linux=utf-8)",
    )
    parser.add_argument(
        "--project_id",
        type=str,
        #default="all",
        default="all",
        help="ID used to refer to the repo",
    )
    parser.add_argument(
        "--output_corpus",
        type=str,
        default="E:/000_Tesis/custom_scripts_d4j/corpus_only_public/",
        help="Path to the output folder",
    )
    parser.add_argument(
        "--tag_focal_context_start",
        type=str,
        default="<FCTX>",
        help="Tag that indicates that the focal context starts",
    )
    parser.add_argument(
        "--tag_focal_context_end",
        type=str,
        default="</FCTX>",
        help="Tag indicating that the focal context ends",
    )
    parser.add_argument(
        "--tag_external_context_start",
        type=str,
        default="<ECTX>",
        help="Tag that indicates that the external context starts",
    )
    parser.add_argument(
        "--tag_external_context_end",
        type=str,
        default="</ECTX>",
        help="Tag that indicates that the external context ends",
    )
    parser.add_argument(
        "--tag_private_focal_context_start",
        type=str,
        default="<PRIVATE_FCTX>",
        help="Tag that indicates that the provate focal context starts",
    )
    parser.add_argument(
        "--tag_private_focal_context_end",
        type=str,
        default="</PRIVATE_FCTX>",
        help="Tag indicating that the private focal context ends",
    )

    return vars(parser.parse_args())


def main():
    args = parse_args()
    input_dataset = args['input_dataset']
    input_encoding = args['input_encoding']
    project_id = args['project_id']
    output_corpus = args['output_corpus']
    tag_focal_context_start = args['tag_focal_context_start']
    tag_focal_context_end = args['tag_focal_context_end']
    tag_external_context_start = args['tag_external_context_start']
    tag_external_context_end = args['tag_external_context_end']
    tag_private_focal_context_start = args['tag_private_focal_context_start']
    tag_private_focal_context_end = args['tag_private_focal_context_end']

    list_projects_d4j = ['Csv', 'Cli', 'Lang', 'Chart', 'Gson']

    if project_id == 'all':
        projects_paths = {}
        for project_df4 in list_projects_d4j:
            projects_paths[project_df4] = []
    elif project_id in list_projects_d4j:
        projects_paths = {
            project_id: []
        }
    else:
        raise 'Project_id not defined'
    
    i = 0
    for project_revision in next(os.walk(input_dataset))[1]:
        path_project = os.path.join(input_dataset, project_revision)
        project_name = project_revision.split("_")[0]

        if project_id == 'all' or project_revision.startswith(project_id):
            #if "Gson_1_f" in path_project:
            projects_paths[project_name].append(path_project)
            i += 1

    print(f"Total corpus to build: {str(i)}")

    start_time = time.time()

    for project_name in projects_paths:
        build_corpus(
            input_dataset, 
            input_encoding, 
            project_name,
            projects_paths[project_name],
            output_corpus, 
            tag_focal_context_start,
            tag_focal_context_end,
            tag_external_context_start,
            tag_external_context_end,
            tag_private_focal_context_start,
            tag_private_focal_context_end
        )

    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_timeformatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))

    print("\n\n\n")
    print(f"Total time seconds: {elapsed_time}")
    print(f"Total time formatted: {elapsed_timeformatted}")


if __name__ == '__main__':
    main()