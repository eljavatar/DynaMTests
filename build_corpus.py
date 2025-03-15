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
# - train
#   - input_methods_src_fm_fc_ms_ff.txt
#   - input_methods_src_fm_fc_dctx.txt
#   - input_methods_src_fm_fc_dctx_priv.txt
#   - output_tests.txt
#   - imports_test_class.txt
#   - imports_focal_class.txt
# - validation
# - test


list_errors_methods_target = []
list_errors_methods_source = []
list_errors_focal_class_sig = []
list_errors_external_class_sig = []
list_errors_focal_signatures = []
list_errors_external_signatures = []



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


def build_corpus(parser_utils: ParserUtils,
                 focal_methods_by_d4j_project: dict[str, set[str]],
                 input_dataset: str,
                 input_encoding: str,
                 output_corpus: str,
                 type_dataset: str,
                 tag_focal_context_start: str,
                 tag_focal_context_end: str,
                 tag_external_context_start: str,
                 tag_external_context_end: str,
                 tag_private_focal_context_start: str,
                 tag_private_focal_context_end: str):
    
    total_repos = get_total_repos(input_dataset)
    print(f"Total repos in dataset {type_dataset}: {str(total_repos)}")
    #total_dataset = get_total_mapped_test_cases(input_dataset)
    #print(f"Total json files in dataset {type_dataset}: {str(total_dataset)}\n\n")

    path_out_courpus_json = os.path.join(output_corpus, "json/" + type_dataset)
    os.makedirs(path_out_courpus_json, exist_ok=True)
    
    path_out_courpus_raw = os.path.join(output_corpus, "raw/" + type_dataset)
    os.makedirs(path_out_courpus_raw, exist_ok=True)
    
    #path_out_courpus_raw = os.path.join(output_corpus, "raw")
    #path_out_courpus_raw_fctx = os.path.join(path_out_courpus_raw, "src_fm_fc_ms_ff/" + type_dataset)
    #path_out_courpus_raw_dctx = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx/" + type_dataset)
    #path_out_courpus_raw_dctx_priv = os.path.join(path_out_courpus_raw, "src_fm_fc_dctx_priv/" + type_dataset)

    #os.makedirs(path_out_courpus_raw_fctx, exist_ok=True)
    #os.makedirs(path_out_courpus_raw_dctx, exist_ok=True)
    #os.makedirs(path_out_courpus_raw_dctx_priv, exist_ok=True)
    

    list_target = []
    list_src_fm_fc_ms_ff = []
    list_src_fm_fc_dctx = []
    list_src_fm_fc_dctx_priv = []
    list_imports_test_class = []
    list_imports_focal_class = []

    #unique_targets = set()
    unique_sources_targets = set()
    focal_methods_existing_in_d4j_dataset: dict[str, int] = {}
    
    index_repo = 1
    for repo_folder in next(os.walk(input_dataset))[1]:
        path_datset_repo = os.path.join(input_dataset, repo_folder)
        path_corpus_repo = os.path.join(path_out_courpus_json, str(repo_folder))
        os.makedirs(path_corpus_repo, exist_ok=True)
        i = 0

        message = f"Building {type_dataset} json corpus repository {repo_folder} - (Nro. repo: {str(index_repo)} of {str(total_repos)})"
        for file in tqdm(os.listdir(path_datset_repo), desc=message):
            if file.endswith('.json'):
                path_json_file_dataset = os.path.join(path_datset_repo, file)

                #print(f"{str(i)} - {file}")
                with open(path_json_file_dataset, encoding=input_encoding) as f:
                    data = json.load(f)

                    target, src_only_method_body, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_test_class, imports_focal_class = extract_data_from_mapped_test_case(
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

                exists_in_d4j_dataset = False
                for d4j_project, focal_methods in focal_methods_by_d4j_project.items():
                    if src_only_method_body in focal_methods:
                        exists_in_d4j_dataset = True
                        if d4j_project in focal_methods_existing_in_d4j_dataset:
                            focal_methods_existing_in_d4j_dataset[d4j_project] += 1
                        else:
                            focal_methods_existing_in_d4j_dataset[d4j_project] = 1
                
                if exists_in_d4j_dataset:
                    continue
                
                source_target = src_only_method_body + target
                if source_target in unique_sources_targets:
                    continue

                unique_sources_targets.add(source_target)

                # continue

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
                
        index_repo += 1
    

    print(f"\nOmmitidos por existir en defects4j")
    for d4j_project, count_existing_focal_methods in focal_methods_existing_in_d4j_dataset.items():
        print(f"{d4j_project} -> {count_existing_focal_methods}")
    
    # return

    total_syntax_errors = (
        len(list_errors_methods_target) 
        + len(list_errors_methods_source) 
        + len(list_errors_focal_class_sig) 
        + len(list_errors_external_class_sig) 
        + len(list_errors_focal_signatures) 
        + len(list_errors_external_signatures)
    )

    print(f"\n\nCount list_errors_methods_target: {len(list_errors_methods_target)}")
    print(f"Count list_errors_methods_source: {len(list_errors_methods_source)}")
    print(f"Count list_errors_focal_class_sig: {len(list_errors_focal_class_sig)}")
    print(f"Count list_errors_external_class_sig: {len(list_errors_external_class_sig)}")
    print(f"Count list_errors_focal_signatures: {len(list_errors_focal_signatures)}")
    print(f"Count list_errors_external_signatures: {len(list_errors_external_signatures)}")
    print(f"Count Total sync errors: {total_syntax_errors}")
    
    # return
    
    print("\nExporting raw corpus")
    export_corpus_raw(
        path_out_courpus_raw, 
        list_target, 
        list_src_fm_fc_ms_ff, 
        list_src_fm_fc_dctx, 
        list_src_fm_fc_dctx_priv, 
        list_imports_focal_class, 
        list_imports_test_class, 
        "Writing raw corpus"
    )

    # export_corpus_raw(
    #     path_out_courpus_raw_dctx, 
    #     list_target, 
    #     list_src_fm_fc_dctx, 
    #     list_imports_focal_class, 
    #     list_imports_test_class, 
    #     "Writing raw corpus list_src_fm_fc_dctx"
    # )

    # export_corpus_raw(
    #     path_out_courpus_raw_dctx_priv, 
    #     list_target, 
    #     list_src_fm_fc_dctx_priv, 
    #     list_imports_focal_class, 
    #     list_imports_test_class, 
    #     "Writing raw corpus list_src_fm_fc_dctx_priv"
    # )

    print(f"\nTotal corpus {type_dataset}: {str(len(list_target))}")
    print(f"\nTotal unique sources-targets: {len(unique_sources_targets)}")
    

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
                      list_input_src_fm_fc_ms_ff: list[str],
                      list_input_src_fm_fc_dctx: list[str],
                      list_input_src_fm_fc_dctx_priv: list[str],
                      list_imports_focal_class: list[str],
                      list_imports_test_class: list[str],
                      msg_tqdm: str):
    
    path_file_input_methods_src_fm_fc_ms_ff = os.path.join(path_out_courpus_raw, "input_methods_src_fm_fc_ms_ff.txt")
    path_file_input_methods_src_fm_fc_dctx = os.path.join(path_out_courpus_raw, "input_methods_src_fm_fc_dctx.txt")
    path_file_input_methods_src_fm_fc_dctx_priv = os.path.join(path_out_courpus_raw, "input_methods_src_fm_fc_dctx_priv.txt")
    path_file_output_tests = os.path.join(path_out_courpus_raw, "output_tests.txt")
    path_file_imports_focal_class = os.path.join(path_out_courpus_raw, "imports_focal_class.txt")
    path_file_imports_test_class = os.path.join(path_out_courpus_raw, "imports_test_class.txt")

    #Removing older version of the file outputs
    if os.path.exists(path_file_input_methods_src_fm_fc_ms_ff):
        os.remove(path_file_input_methods_src_fm_fc_ms_ff)
    
    if os.path.exists(path_file_input_methods_src_fm_fc_dctx):
        os.remove(path_file_input_methods_src_fm_fc_dctx)
    
    if os.path.exists(path_file_input_methods_src_fm_fc_dctx_priv):
        os.remove(path_file_input_methods_src_fm_fc_dctx_priv)

    if os.path.exists(path_file_output_tests):
        os.remove(path_file_output_tests)

    if os.path.exists(path_file_imports_focal_class):
        os.remove(path_file_imports_focal_class)

    if os.path.exists(path_file_imports_test_class):
        os.remove(path_file_imports_test_class)

    #Writing to file
    with (
        open(path_file_input_methods_src_fm_fc_ms_ff, 'w', encoding='utf-8') as f_in_src_fm_fc_ms_ff, 
        open(path_file_input_methods_src_fm_fc_dctx, 'w', encoding='utf-8') as f_in_src_fm_fc_dctx, 
        open(path_file_input_methods_src_fm_fc_dctx_priv, 'w', encoding='utf-8') as f_in_src_fm_fc_dctx_priv, 
        open(path_file_output_tests, 'w', encoding='utf-8') as f_out, 
        open(path_file_imports_focal_class, 'w', encoding='utf-8') as f_imp_f, 
        open(path_file_imports_test_class, 'w', encoding='utf-8') as f_imp_t
    ):
        for index in tqdm(range(len(list_input_src_fm_fc_ms_ff)), desc=msg_tqdm):
            f_in_src_fm_fc_ms_ff.write(list_input_src_fm_fc_ms_ff[index] + "\n")
            f_in_src_fm_fc_dctx.write(list_input_src_fm_fc_dctx[index] + "\n")
            f_in_src_fm_fc_dctx_priv.write(list_input_src_fm_fc_dctx_priv[index] + "\n")
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
        return None, None, None, None, None, None, None

    if ('abstract' in focal_method['modifiers']):
        return None, None, None, None, None, None, None
    
    if ('@Ignore' in test_case['modifiers']):
        return None, None, None, None, None, None, None

    target = clean_comments_in_code(parser_utils, test_case['body'])
    target = target.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")
    target = parser_utils.fix_type_parameters_inconsistences(target)

    body_method = clean_comments_in_code(parser_utils, focal_method['body'])
    body_method = body_method.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("){", ") {").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")
    body_method = parser_utils.fix_type_parameters_inconsistences(body_method)

    target_is_empty = parser_utils.method_body_is_empty(target)
    body_method_is_empty = parser_utils.method_body_is_empty(body_method)

    if target_is_empty or body_method_is_empty:
        return None, None, None, None, None, None, None
    

    #focal_sigs = f"{used_non_private_signatures_of_class_str} {used_private_signatures_of_class_str} {non_private_fields_str} {constructors_str} {non_private_methods_str}"
    #code_to_validate_focal_sig = "public interface AnyClass { " + focal_sigs + " }" 
    code_to_validate_target = "public class AnyClass { " + target + " }" 
    validate_target = parser_utils.validate_if_code_has_errors(code_to_validate_target, True)
    if validate_target == True:
        # print("\n\n\n\n")
        # print(f"File error Target method: {file} \n")
        # print(target)
        # print("\n\n\n\n"
        list_errors_methods_target.append(f"File error Target Method: {file} \n\n{target}")
        return None, None, None, None, None, None, None
    

    code_to_validate_source = "public class AnyClass { " + body_method + " }" 
    validate_source = parser_utils.validate_if_code_has_errors(code_to_validate_source, True)
    if validate_source == True:
        # print("\n\n\n\n")
        # print(f"File error Source method: {file} \n")
        # print(body_method)
        # print("\n\n\n\n")
        list_errors_methods_source.append(f"File error Source Method: {file} \n\n{body_method}")
        return None, None, None, None, None, None, None


    src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv = build_format_corpus(
        parser_utils,
        focal_class, 
        focal_method, 
        body_method,
        tag_focal_context_start, 
        tag_focal_context_end, 
        tag_external_context_start, 
        tag_external_context_end,
        tag_private_focal_context_start,
        tag_private_focal_context_end, file
    )

    if src_fm_fc_ms_ff is None:
        return None, None, None, None, None, None, None

    imports_test_class = clean_comments_in_code(parser_utils, '|'.join(test_class['imports']))
    imports_test_class = imports_test_class.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    imports_focal_class = clean_comments_in_code(parser_utils, '|'.join(focal_class['imports']))
    imports_focal_class = imports_focal_class.replace(" . ", ".").replace(". ", ".").replace(" .", ".")

    return target, body_method, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_test_class, imports_focal_class


def build_format_corpus(parser_utils: ParserUtils,
                        focal_class: dict,
                        focal_method: dict,
                        body_method: str,
                        tag_focal_context_start: str,
                        tag_focal_context_end: str,
                        tag_external_context_start: str,
                        tag_external_context_end: str,
                        tag_private_focal_context_start: str,
                        tag_private_focal_context_end: str, file):
    
    # ADD static_initializer from mining: For next version
    
    # format_class_signature = '{} {} {}'
    # class_signature = format_class_signature.format(focal_class['class_name'], focal_class['superclass'], focal_class['interfaces']).strip()
    # class_signature = focal_class['class_signature'].strip()
    # class_signature = clean_comments_in_code(parser_utils, class_signature)
    # class_signature = clean_class_signature_annotations(parser_utils, class_signature)
    # class_signature = class_signature.replace("{", "") # En caso de que en el minado se extraiga como: public class Clase \n{

    class_signature = build_class_signature(parser_utils, focal_class)

    code_to_validate_class_sig = class_signature + " { }"
    validate_code_class_sig = parser_utils.validate_if_code_has_errors(code_to_validate_class_sig, False)
    if validate_code_class_sig == True:
        # print("\n\n\n\n")
        # print(f"File error Class Signature: {file} \n")
        # print(class_signature)
        # print("\n\n\n\n")
        list_errors_focal_class_sig.append(f"File error Class Signature: {file} \n{class_signature}")
        return None, None, None

    focal_class_methods = focal_class['methods']
    focal_class_fields = focal_class['fields']

    key_method_for_extract = 'full_signature'
    # key_method_for_extract = 'full_signature_parameters'

    constructors = [meth[key_method_for_extract] + ";" for meth in focal_class_methods if meth['is_constructor'] == True]
    constructors_str = '\n'.join(constructors)
    constructors_str = clean_comments_in_code(parser_utils, constructors_str)
    constructors_str = parser_utils.fix_type_parameters_inconsistences(constructors_str)

    non_private_methods = [meth[key_method_for_extract] + ";" for meth in focal_class_methods if meth['is_constructor'] == False and 'private' not in meth['modifiers']]
    non_private_methods_str = '\n'.join(non_private_methods)
    non_private_methods_str = clean_comments_in_code(parser_utils, non_private_methods_str)
    non_private_methods_str = parser_utils.fix_type_parameters_inconsistences(non_private_methods_str)

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
    src_fm_fc_ms_ff = src_fm_fc_ms_ff.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")


    class_private_deps_used = focal_method['class_private_deps_used']
    class_private_deps_used_methods = class_private_deps_used['methods']
    class_private_deps_used_fields = class_private_deps_used['fields']

    # Extract all private constructors
    used_private_signatures_of_class = [meth[key_method_for_extract] + ";" for meth in focal_class_methods if 'private' in meth['modifiers'] and meth['is_constructor'] == True]
    # Extract private methods and fields of class used in focal method
    used_private_signatures_of_class.extend([meth[key_method_for_extract] + ";" for meth in class_private_deps_used_methods if 'private' in meth['modifiers'] and meth['is_constructor'] == False])
    used_private_signatures_of_class.extend([field['original_string'] for field in class_private_deps_used_fields if 'private' in field['modifier']])
    used_private_signatures_of_class_str = '\n'.join(used_private_signatures_of_class)
    used_private_signatures_of_class_str = clean_comments_in_code(parser_utils, used_private_signatures_of_class_str)
    used_private_signatures_of_class_str = parser_utils.fix_type_parameters_inconsistences(used_private_signatures_of_class_str)

    #used_private_signatures_of_class = set(clean_comments_in_code(meth['full_signature_parameters']) + ";" for meth in focal_class_methods if meth['is_constructor'] == True and 'private' in meth['modifiers'])
    #used_private_signatures_of_class.update(focal_method['used_private_signatures_of_class'])
    #used_private_signatures_of_class_str = ' '.join(used_private_signatures_of_class)

    class_non_private_deps_used = focal_method['class_non_private_deps_used']
    class_non_private_deps_used_methods = class_non_private_deps_used['methods']
    class_non_private_deps_used_fields = class_non_private_deps_used['fields']

    # Extract all public constructors
    used_non_private_signatures_of_class = [meth[key_method_for_extract] + ";" for meth in focal_class_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == True]
    # Extract non private methods and fields of class used in focal method
    used_non_private_signatures_of_class.extend([meth[key_method_for_extract] + ";" for meth in class_non_private_deps_used_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == False])
    used_non_private_signatures_of_class.extend([field['original_string'] for field in class_non_private_deps_used_fields if 'private' not in field['modifier']])
    used_non_private_signatures_of_class_str = '\n'.join(used_non_private_signatures_of_class)
    used_non_private_signatures_of_class_str = clean_comments_in_code(parser_utils, used_non_private_signatures_of_class_str)
    used_non_private_signatures_of_class_str = parser_utils.fix_type_parameters_inconsistences(used_non_private_signatures_of_class_str)

    #used_non_private_signatures_of_class = set(clean_comments_in_code(meth['full_signature_parameters']) + ";" for meth in focal_class_methods if meth['is_constructor'] == True and 'private' not in meth['modifiers'])
    #used_non_private_signatures_of_class.update(focal_method['used_non_private_signatures_of_class'])
    #used_non_private_signatures_of_class_str = ' '.join(used_non_private_signatures_of_class)


    external_context = []

    external_dependencies = focal_method['external_dependencies']
    for ext_dep in external_dependencies:
        ext_class_sig = ext_dep['class_signature']
        ext_class_sig_cleaned = clean_comments_in_code(parser_utils, ext_class_sig)
        ext_class_sig_cleaned = clean_class_signature_annotations(parser_utils, ext_class_sig_cleaned)
        ext_class_sig_cleaned = ext_class_sig_cleaned.replace("{", "") # En caso de que en el minado se extraiga como: public class Clase \n{
        ext_class_sig_cleaned = parser_utils.fix_close_type_parameter_sig_class(ext_class_sig_cleaned)

        # ext_class_sig_cleaned = build_class_signature(parser_utils, ext_dep)

        code_to_validate_ext_class_sig = ext_class_sig_cleaned + " { }"
        validate_code_ext_class_sig = parser_utils.validate_if_code_has_errors(code_to_validate_ext_class_sig, False)
        if validate_code_ext_class_sig == True:
            # print("\n\n\n\n")
            # print(f"File error External Class Signature: {file} \n")
            # print(ext_class_sig_cleaned)
            # print("\n\n\n\n")
            list_errors_external_class_sig.append(f"File error External Class Signature: {file} \n{ext_class_sig_cleaned}")
            return None, None, None

        ext_fields = ext_dep['fields']
        ext_methods = ext_dep['methods']
        signatures_by_ext_class = [field['original_string'] for field in ext_fields]
        signatures_by_ext_class.extend([meth[key_method_for_extract] + ";" for meth in ext_methods])
        
        signatures_by_ext_class_str = '\n'.join(signatures_by_ext_class)
        signatures_by_ext_class_str = clean_comments_in_code(parser_utils, signatures_by_ext_class_str)
        signatures_by_ext_class_str = parser_utils.fix_type_parameters_inconsistences(signatures_by_ext_class_str)
        signatures_by_ext_class_str = clean_methods_signatures_annotations(parser_utils, signatures_by_ext_class_str)

        code_to_validate_ext_sig = "public interface AnyClass { " + signatures_by_ext_class_str + " }" 
        validate_code_ext_sig = parser_utils.validate_if_code_has_errors(code_to_validate_ext_sig, False)
        if validate_code_ext_sig == True:
            # print("\n\n\n\n")
            # print(f"File error External Signatures: {file} \n")
            # print(signatures_by_ext_class_str)
            # print("\n\n\n\n")

            list_errors_external_signatures.append(f"File error External Signatures: {file} \n\n{code_to_validate_ext_sig}")
            return None, None, None

        format_src_ext_class = '{} {{ {} }}'
        src_ext_class = format_src_ext_class.format(ext_class_sig_cleaned, signatures_by_ext_class_str)
        # src_ext_class = clean_comments_in_code(parser_utils, src_ext_class)
        src_ext_class = clean_tabs_and_new_lines(src_ext_class)
        external_context.append(tag_external_context_start + src_ext_class + tag_external_context_end)

    if len(external_context) == 0:
        src_external_context = tag_external_context_start + tag_external_context_end
    else:
        src_external_context = ' '.join(external_context).strip()

    # signatures_of_external_dependencies = focal_method['signatures_of_external_dependencies']
    
    # for ext_class_sig in signatures_of_external_dependencies:
    #     signatures_by_ext_class = signatures_of_external_dependencies[ext_class_sig]
    #     ext_class_sig_cleaned = clean_comments_in_code(parser_utils, ext_class_sig)
    #     signatures_by_ext_class_str = '\n'.join(signatures_by_ext_class)
    #     signatures_by_ext_class_str = clean_comments_in_code(parser_utils, signatures_by_ext_class_str)
        
    #     format_src_ext_class = '{} {{ {} }}'
    #     src_ext_class = format_src_ext_class.format(ext_class_sig_cleaned, signatures_by_ext_class_str)
    #     #src_ext_class = clean_comments_in_code(parser_utils, src_ext_class)
    #     external_context.append(src_ext_class)
    
    # external_context_str = '\n'.join(external_context).strip()
    # external_context_str = clean_comments_in_code(parser_utils, external_context_str)
    # src_external_context = tag_external_context_start + external_context_str + tag_external_context_end

    focal_sigs = f"{used_non_private_signatures_of_class_str} {used_private_signatures_of_class_str} {non_private_fields_str} {constructors_str} {non_private_methods_str}"
    code_to_validate_focal_sig = "public interface AnyClass { " + focal_sigs + " }" 
    validate_code_focal_sig = parser_utils.validate_if_code_has_errors(code_to_validate_focal_sig, False)
    if validate_code_focal_sig == True:
        # print("\n\n\n\n")
        # print(f"File error Focal Signatures: {file} \n")
        # print(code_to_validate_focal_sig)
        # print("\n\n\n\n")
        list_errors_focal_signatures.append(f"File error Focal Signatures: {file} \n\n{code_to_validate_focal_sig}")
        return None, None, None


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
    src_fm_fc_dctx = src_fm_fc_dctx.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")


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
    src_fm_fc_dctx_priv = clean_tabs_and_new_lines(src_fm_fc_dctx_priv)
    src_fm_fc_dctx_priv = src_fm_fc_dctx_priv.replace(" . ", ".").replace(". ", ".").replace(" .", ".").replace("( ", "(").replace(" )", ")").replace("[ ", "[").replace(" ]", "]")


    return src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv



def build_class_signature(parser_utils: ParserUtils, class_dict: dict) -> str:
    class_name = class_dict['class_name']
    extends = class_dict['superclass']
    implements = class_dict['interfaces']

    class_signature: str = class_dict['class_signature'].strip()
    class_signature = clean_comments_in_code(parser_utils, class_signature)
    class_signature = clean_class_signature_annotations(parser_utils, class_signature)
    class_signature = class_signature.replace("{", "")

    index = class_signature.find(class_name)

    if index != -1:
        modifiers_and_type = class_signature[:index]
        format_class_signature = '{} {} {} {}'
        class_signature = format_class_signature.format(modifiers_and_type, class_name, extends, implements).strip()

    # class_signature = clean_comments_in_code(parser_utils, class_signature)
    # class_signature = clean_class_signature_annotations(parser_utils, class_signature)
    # class_signature = class_signature.replace("{", "")

    return class_signature


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


def clean_class_signature_annotations(parser_utils: ParserUtils, signature: str) -> str:
    modified_code = parser_utils.clean_annotations(signature)
    return modified_code.strip()


def clean_methods_signatures_annotations(parser_utils: ParserUtils, signature: str) -> str:
    modified_code = parser_utils.clean_signatures_annotations(signature)
    return modified_code.strip()



def get_focal_methods_by_d4j_project(parser_utils: ParserUtils, validate_against_d4j_dataset: bool, d4j_dataset: str, input_encoding: str):
    focal_methods_by_d4j_project: dict[str, set[str]] = {}

    if validate_against_d4j_dataset:
        # list_projects_d4j = ['Csv', 'Cli', 'Lang', 'Chart', 'Gson']
        list_projects_d4j = ['Closure', 'Cli', 'Codec', 'Collections', 'Compress', 'Csv', 'JxPath', 'Lang', 'Math', 'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Chart', 'Time', 'Jsoup', 'Mockito']
        
        for d4j_project in tqdm(list_projects_d4j, desc="Extrayendo metadata de d4j_dataset"):
            path_d4j_project_dataset = os.path.join(d4j_dataset, d4j_project)

            focal_methods = set()

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
            
            focal_methods_by_d4j_project[d4j_project] = focal_methods

    return focal_methods_by_d4j_project


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
        "--validate_against_d4j_dataset",
        type=bool,
        default=True,
        help="Indicates wether to skip including tests from the d4j dataset",
    )
    parser.add_argument(
        "--d4j_dataset",
        type=str,
        default="/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version",
        help="Path to the d4j dataset",
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
    type_dataset = args['type_dataset']
    validate_against_d4j_dataset = args['validate_against_d4j_dataset']
    d4j_dataset = args['d4j_dataset']
    output_corpus = args['output_corpus']
    tag_focal_context_start = args['tag_focal_context_start']
    tag_focal_context_end = args['tag_focal_context_end']
    tag_external_context_start = args['tag_external_context_start']
    tag_external_context_end = args['tag_external_context_end']
    tag_private_focal_context_start = args['tag_private_focal_context_start']
    tag_private_focal_context_end = args['tag_private_focal_context_end']

    start_time = time.time()

    parser_utils = ParserUtils(input_encoding)

    focal_methods_by_d4j_project = get_focal_methods_by_d4j_project(parser_utils, validate_against_d4j_dataset, d4j_dataset, input_encoding)
    
    build_corpus(
        parser_utils,
        focal_methods_by_d4j_project,
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
    # list_errors_methods_target = []
    # list_errors_methods_source = []
    # #LIST_ERRORS_
    # list_errors_focal_signatures = []
    # list_errors_external_signatures = []
    main()