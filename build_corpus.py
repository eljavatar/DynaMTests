import argparse
import copy
import json
import os
import re
import time
from tqdm import tqdm
from ParserUtils import ParserUtils


# Salidas:
# corpus/json
# - train
#   - repo_id
#     - repo_id_n_corpus.json
#       Cada json tiene la siguiente estructura:
#       {
#          "target": "",
#          "src_fm_fc_ms_ff": "",
#          "src_fm_fc_dctx": "dctx: dynamic context",
#          "src_fm_fc_dctx_priv": "",
#          "imports_test_class": "",
#          "imports_focal_class": ""
#       }
# - validation
# - test

# corpus/raw
# - src_fm_fc_ms_ff
#   - train
#     - input_methods.txt
#     - output_tests.txt
#     - imports_test_class.txt
#     - imports_focal_class.txt
#   - validation
#   - test
# - src_fm_fc_dctx
# - src_fm_fc_dctx_priv


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


def get_total_mapped_test_cases(path: str):
    total_json_files = 0
    # Recorre las carpetas y archivos en el directorio indicado
    # for carpeta in next(os.walk('.'))[1]: # Directorio actual
    for folder in next(os.walk(path))[1]:
        path_folder = os.path.join(path, folder)
        # Contador para archivos .json en la carpeta actual
        json_count = 0
        for file in os.listdir(path_folder):
            if file.endswith('.json'):
                json_count += 1
        #print(f'En la carpeta {carpeta} hay {contador_json} archivos .json')
        total_json_files += json_count
    return total_json_files


def build_corpus(input_dataset: str,
                 input_encoding: str,
                 output_corpus: str,
                 type_dataset: str,
                 tag_focal_context_start: str,
                 tag_focal_context_end: str,
                 tag_external_context_start: str,
                 tag_external_context_end: str,
                 tag_private_focal_context_start: str,
                 tag_private_focal_context_end: str):
    
    parser_utils = ParserUtils(input_encoding)
    
    total_repos = get_total_repos(input_dataset)
    print(f"Total repos in dataset {type_dataset}: {str(total_repos)}")
    #total_dataset = get_total_mapped_test_cases(input_dataset)
    #print(f"Total json files in dataset {type_dataset}: {str(total_dataset)}\n\n")

    path_out_courpus_json = os.path.join(output_corpus, "json/" + type_dataset)
    os.makedirs(path_out_courpus_json, exist_ok=True)
    
    
    path_out_courpus_raw = os.path.join(output_corpus, "raw")
    path_out_courpus_raw_fctx = os.path.join(path_out_courpus_raw, "src_fm_fc_ms_ff/" + type_dataset)
    path_out_courpus_raw_dctx = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx/" + type_dataset)
    path_out_courpus_raw_dctx_priv = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx_priv/" + type_dataset)

    os.makedirs(path_out_courpus_raw_fctx, exist_ok=True)
    os.makedirs(path_out_courpus_raw_dctx, exist_ok=True)
    os.makedirs(path_out_courpus_raw_dctx_priv, exist_ok=True)
    

    list_target = []
    list_src_fm_fc_ms_ff = []
    list_src_fm_fc_dctx = []
    list_src_fm_fc_dctx_priv = []
    list_imports_test_class = []
    list_imports_focal_class = []

    unique_targets = set()
    
    index_repo = 1
    for repo_folder in next(os.walk(input_dataset))[1]:
        path_datset_repo = os.path.join(input_dataset, repo_folder)
        path_corpus_repo = os.path.join(path_out_courpus_json, str(repo_folder))
        os.makedirs(path_corpus_repo, exist_ok=True)
        i = 0

        message = f"Building json corpus repository {repo_folder} - (Nro. repo: {str(index_repo)} of {str(total_repos)})"
        for file in tqdm(os.listdir(path_datset_repo), desc=message):
            if file.endswith('.json'):
                path_json_file_dataset = os.path.join(path_datset_repo, file)

                #print(f"{str(i)} - {file}")
                with open(path_json_file_dataset, encoding=input_encoding) as f:
                    data = json.load(f)

                    target, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_test_class, imports_focal_class = extract_data_from_mapped_test_case(
                        parser_utils,
                        data, 
                        tag_focal_context_start, 
                        tag_focal_context_end, 
                        tag_external_context_start, 
                        tag_external_context_end,
                        tag_private_focal_context_start,
                        tag_private_focal_context_end, file)
                
                if target is None:
                    continue
                
                if target in unique_targets:
                    continue

                unique_targets.add(target)

                file_without_extension = file.split('.')[0]
                file_corpus_json = file_without_extension + "_corpus.json"
                path_file_corpus_json = os.path.join(path_corpus_repo, file_corpus_json)

                data_json = {
                    'target': target,
                    'src_fm_fc_ms_ff': src_fm_fc_ms_ff,
                    'src_fm_fc_dctx': src_fm_fc_dctx,
                    'src_fm_fc_dctx_priv': src_fm_fc_dctx_priv,
                    'imports_focal_class': imports_focal_class,
                    'imports_test_class': imports_test_class
                }

                export_corpus_json(data_json, path_file_corpus_json)

                list_target.append(target)
                list_src_fm_fc_ms_ff.append(src_fm_fc_ms_ff)
                list_src_fm_fc_dctx.append(src_fm_fc_dctx)
                list_src_fm_fc_dctx_priv.append(src_fm_fc_dctx_priv)
                list_imports_focal_class.append(imports_focal_class)
                list_imports_test_class.append(imports_test_class)

                i += 1

                #if i > 10:
                #    return
                
        #if index_repo >= 732:
        #    break
        index_repo += 1
    
    
    print("\nExporting raw corpus")
    export_corpus_raw(
        path_out_courpus_raw_fctx, 
        list_target, 
        list_src_fm_fc_ms_ff, 
        list_imports_focal_class, 
        list_imports_test_class, 
        "Writing raw corpus list_src_fm_fc_ms_ff"
    )

    export_corpus_raw(
        path_out_courpus_raw_dctx, 
        list_target, 
        list_src_fm_fc_dctx, 
        list_imports_focal_class, 
        list_imports_test_class, 
        "Writing raw corpus list_src_fm_fc_dctx"
    )

    export_corpus_raw(
        path_out_courpus_raw_dctx_priv, 
        list_target, 
        list_src_fm_fc_dctx_priv, 
        list_imports_focal_class, 
        list_imports_test_class, 
        "Writing raw corpus list_src_fm_fc_dctx_priv"
    )

    print(f"\nTotal corpus {type_dataset}: {str(len(list_target))}")
    print(f"\nTotal unique targets: {len(unique_targets)}")
    

def export_corpus_json(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        data_json = json.dumps(data)
        f.write(data_json)


def export_corpus_raw(path_out_courpus_raw: str, 
                      list_target: list[str], 
                      list_input: list[str],
                      list_imports_focal_class: list[str],
                      list_imports_test_class: list[str],
                      msg_tqdm: str):
    
    path_file_input_methods = os.path.join(path_out_courpus_raw, "input_methods.txt")
    path_file_output_tests = os.path.join(path_out_courpus_raw, "output_tests.txt")
    path_file_imports_focal_class = os.path.join(path_out_courpus_raw, "imports_focal_class.txt")
    path_file_imports_test_class = os.path.join(path_out_courpus_raw, "imports_test_class.txt")

    #Removing older version of the file outputs
    if os.path.exists(path_file_input_methods):
        os.remove(path_file_input_methods)

    if os.path.exists(path_file_output_tests):
        os.remove(path_file_output_tests)

    if os.path.exists(path_file_imports_focal_class):
        os.remove(path_file_imports_focal_class)

    if os.path.exists(path_file_imports_test_class):
        os.remove(path_file_imports_test_class)

    #Writing to file
    with open(path_file_input_methods, 'w', encoding='utf-8') as f_in, open(path_file_output_tests, 'w', encoding='utf-8') as f_out, open(path_file_imports_focal_class, 'w', encoding='utf-8') as f_imp_f, open(path_file_imports_test_class, 'w', encoding='utf-8') as f_imp_t:
        for index in tqdm(range(len(list_input)), desc=msg_tqdm):
            f_in.write(list_input[index] + "\n")
            f_out.write(list_target[index] + "\n")
            f_imp_f.write(list_imports_focal_class[index] + "\n")
            f_imp_t.write(list_imports_test_class[index] + "\n")


def extract_data_from_mapped_test_case(parser_utils: ParserUtils,
                                       data: dict,
                                       tag_focal_context_start: str,
                                       tag_focal_context_end: str,
                                       tag_external_context_start: str,
                                       tag_external_context_end: str,
                                       tag_private_focal_context_start: str,
                                       tag_private_focal_context_end: str, file):
    test_class = data['test_class']
    test_case = data['test_case']
    focal_class = data['focal_class']
    focal_method = data['focal_method']
    #repository = data['repository']

    if (' interface ' in focal_class['class_signature'] 
            or focal_class['class_signature'].startswith('interface ')):
        return None, None, None, None, None, None

    if ('abstract' in focal_method['modifiers']):
        return None, None, None, None, None, None

    target = clean_comments_in_code(parser_utils, test_case['body'])
    target = target.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

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

    imports_test_class = clean_tabs_and_new_lines('|'.join(test_class['imports']))
    imports_test_class = imports_test_class.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    imports_focal_class = clean_tabs_and_new_lines('|'.join(focal_class['imports']))
    imports_focal_class = imports_focal_class.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    return target, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_test_class, imports_focal_class


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

    #used_private_signatures_of_class = set(clean_comments_in_code(meth['full_signature_parameters']) + ";" for meth in focal_class_methods if meth['is_constructor'] == True and 'private' in meth['modifiers'])
    #used_private_signatures_of_class.update(focal_method['used_private_signatures_of_class'])
    #used_private_signatures_of_class_str = ' '.join(used_private_signatures_of_class)

    used_non_private_signatures_of_class = [meth['full_signature_parameters'] + ";" for meth in focal_class_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == True]
    used_non_private_signatures_of_class.extend([meth['full_signature_parameters'] + ";" for meth in focal_method['class_private_deps_used']['methods'] if 'private' not in meth['modifiers'] and meth['is_constructor'] == False])
    used_non_private_signatures_of_class.extend([field['original_string'] for field in focal_method['class_private_deps_used']['fields'] if 'private' not in field['modifier']])
    used_non_private_signatures_of_class_str = '\n'.join(used_non_private_signatures_of_class)
    used_non_private_signatures_of_class_str = clean_comments_in_code(parser_utils, used_non_private_signatures_of_class_str)

    #used_non_private_signatures_of_class = set(clean_comments_in_code(meth['full_signature_parameters']) + ";" for meth in focal_class_methods if meth['is_constructor'] == True and 'private' not in meth['modifiers'])
    #used_non_private_signatures_of_class.update(focal_method['used_non_private_signatures_of_class'])
    #used_non_private_signatures_of_class_str = ' '.join(used_non_private_signatures_of_class)

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
        #default="E:/000_Tesis/project_tesis_build_dataset/output",
        #default="E:/000_Tesis/project_tesis_build_dataset/mining_results/test3/output",
        default="E:/000_Tesis/project_tesis_build_dataset/dataset/train",
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
        "--type_dataset",
        type=str,
        default="train",
        help="Type of dataset to which the corpus will be generated",
    )
    parser.add_argument(
        "--output_corpus",
        type=str,
        default="E:/000_Tesis/project_tesis_build_dataset/corpus/",
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
    output_corpus = args['output_corpus']
    type_dataset = args['type_dataset']
    tag_focal_context_start = args['tag_focal_context_start']
    tag_focal_context_end = args['tag_focal_context_end']
    tag_external_context_start = args['tag_external_context_start']
    tag_external_context_end = args['tag_external_context_end']
    tag_private_focal_context_start = args['tag_private_focal_context_start']
    tag_private_focal_context_end = args['tag_private_focal_context_end']

    start_time = time.time()
    build_corpus(
        input_dataset, 
        input_encoding, 
        output_corpus, 
        type_dataset,
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