import argparse
import shutil
import subprocess
import copy
import json
import stat
import os
import sys
import traceback
import time
import functools
from multiprocessing import Pool
from functools import partial
from tqdm import tqdm
from typing import List, Dict, Any, Set, Optional
from ClassParser import ClassParser
from DependencyClassParser import DependencyClassParser
import textwrap
import glob
from dependency_parser_utils import DependencyParserUtils


def get_class_path(start_path: str, filename: str, path_focal_class: str) -> str:
    for root, dirs, files in os.walk(start_path):
        if filename in files:
            path_find = os.path.join(root, filename)
            if path_find.endswith(path_focal_class):
                return path_find
    return None


def copy_error_files(path_by_type_error, project_name_version, output_empty, dataset_out, files):
    dir_empty_by_type_error = os.path.join(output_empty, path_by_type_error + str(project_name_version))
    os.makedirs(dir_empty_by_type_error, exist_ok=True)
    for file in files:
        shutil.copy(os.path.join(dataset_out, file), dir_empty_by_type_error)


def analyze_project(project_path: str, 
                    project_id: str, 
                    focal_classes_content: list[dict], 
                    test_and_src_paths_by_project_and_version: dict[str, dict[str, str]], 
                    output: str, 
                    output_empty: str):
    """
    Analyze a single project
    """
    #directories = project_path.split("/")
    #last_directory = "/".join(directories[:-1]).strip()
    project_name_version = os.path.split(project_path)[-1]

    #Create folders
    #d4j_project_id_path = os.path.join(output, str(project_id))
    #os.makedirs(d4j_project_id_path, exist_ok=True)
    #dataset_out = os.path.join(d4j_project_id_path, str(last_directory))
    dataset_out = os.path.join(output, str(project_name_version))
    
    # if "Time_27_f" != project_name_version:
    #     return
    # print(f"\n\nproject_path: {project_path}\n\n")
    
    # print(f"project_name_version: {project_name_version} -> dataset_out: {dataset_out}")
    # return

    os.makedirs(dataset_out, exist_ok=True)

    #Run analysis
    language = 'java'
    print(f"Extracting and mapping classes from project {project_id} ({project_name_version})...")
    result_analyze_project = find_focal_classes(
        project_path, 
        language, 
        dataset_out, 
        project_id, 
        project_name_version, 
        focal_classes_content, 
        test_and_src_paths_by_project_and_version
    )
    (tot_fclasses, tot_mfm_by_focal, tot_mfm, repo_exists, error_finding_java_files) = result_analyze_project

    if tot_mfm == 0:
        files = os.listdir(dataset_out)

        if not repo_exists:
            copy_error_files("1_repo_not_exists/", project_name_version, output_empty, dataset_out, files)
        elif error_finding_java_files:
            copy_error_files("2_error_finding_java_files/", project_name_version, output_empty, dataset_out, files)
        else:
            copy_error_files("3_not_mapping_focal_methods/", project_name_version, output_empty, dataset_out, files)

        shutil.rmtree(dataset_out, ignore_errors=True)

    #Print Stats
    print(f"\n\n---- Results Project {project_id} ({project_name_version}) ----")
    print("Total Focal Classes: " + str(tot_fclasses))
    print("Total Classes with MFM: " + str(tot_mfm_by_focal))
    print("Mapped Focal Methods (MFM): " + str(tot_mfm))
    print()


def find_focal_classes(root, 
                       language, 
                       output, 
                       project_id: str, 
                       project_name_version: str, 
                       focal_classes_content: list[dict], 
                       test_and_src_paths_by_project_and_version: dict[str, dict[str, str]]):
    """
    Find all classes exclude tests
    Finds test cases using @Test annotation
    """
    #Logging
    log_path = os.path.join(output, "log.txt")
    log = open(log_path, "w", encoding="utf-8")
    log.write(f"PROJECT {project_id} ({project_name_version})" + '\n')
    log.write("==================================================" + '\n')

    repo_exists: bool = True
    error_finding_java_files: bool = False

    #Move to folder when repo was cloned
    if os.path.exists(root):
        os.chdir(root)
    else:
        #print("Path repo not exists: " + root + '\n')
        log.write("Path repo not exists: " + root + '\n')
        log.close()
        repo_exists = False
        return 0, 0, 0, repo_exists, True
    
    #Test Classes
    try:
        result = subprocess.check_output(r'grep -l -r @Test --include \*.java', shell=True)
        #result = subprocess.check_output(r'grep -l -r @Test --include \*\\.java', shell=True)
        tests = result.decode('ascii').splitlines()
    except subprocess.CalledProcessError as e:
        tests = []
        if e.returncode != 1:
            print(f"\nCalledProcessError during grep Test classes: {str(e)}")
            #error_finding_java_files = True
            error_trace = ''.join(traceback.TracebackException.from_exception(e).format())
            log.write(f"\nCalledProcessError during grep Test classes: {str(e)}\n")
            log.write(error_trace)
            #log.close()
        
        #return 0, 0, 0, repo_exists, repo_has_test_files, error_finding_java_files
    except Exception as ex:
        tests = []
        print(f"\nUnknownError during grep Test classes: {str(ex)}")
        #error_finding_java_files = True
        error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        log.write(f"\nUnknownError during grep Test classes: {str(ex)}\n")
        log.write(error_trace)
        #log.close()
        #return 0, 0, 0, repo_exists, repo_has_test_files, error_finding_java_files
    
    #print("\n\nList tests")
    #print(tests)
    #print("")

    #Java Files
    try:
        # Con glob, se soluciona el error que se lanza cuando hay un archivo .java en la ruta raíz del proyecto
        all_java = glob.glob('**/*.java', recursive=True)
        all_java = [path.replace("\\", "/") for path in all_java] # For Windows

        #result = subprocess.check_output(['find', '-name', '*.java'])

        #result = subprocess.check_output(['find', '-name', '*.java', '-print0'], shell=True)
        #all_java = result.decode('ascii').split('\0')[:-1]
        
        #result = subprocess.check_output(['find', '-name', '*.java'], shell=True)
        #result = subprocess.check_output(['find', root, '-name', '*.java'], shell=True)
        #result = subprocess.check_output(['find', '.', '-name', '*.java'], shell=True)
        #all_java = result.decode('ascii').splitlines()
        all_java = [j.replace("./", "") for j in all_java]
    except Exception as ex:
        print("Error during find java files: " + str(ex) + '\n')
        error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        log.write("Error during find java files: " + str(ex) + '\n')
        log.write(error_trace)
        log.close()
        error_finding_java_files = True
        return 0, 0, 0, repo_exists, error_finding_java_files
    
    #print("\n\nList java files: " + str(len(all_java)))
    #print(all_java)
    #print("")

    # All Classes exclude tests
    focals = list(set(all_java) - set(tests))
    focals = [f for f in focals if not "src/test" in f]
    #focals_norm = [f.lower() for f in focals]

    log.write("Java Files: " + str(len(all_java)) + '\n')
    log.write("Test Classes: " + str(len(tests)) + '\n')
    log.write("Potential Focal Classes: " + str(len(focals)) + '\n')
    log.flush()

    #Stats
    tot_fclasses = len(focals)
    #tot_fclasses_in_json
    tot_mfm = 0

    # Extract info from Focal Classes
    log.write("Extract info from Focal Classes" '\n')
    mfm_by_focal_list = list()

    parser = ClassParser(language)
    dependency_parser = DependencyClassParser(language)
    parserutils = DependencyParserUtils()

    index = 0

    log_error_mapping_path = os.path.join(output, "log_error_mapping.txt")
    log_error_mapping = open(log_error_mapping_path, "w", encoding="utf-8")
    log_error_mapping.write(f"PROJECT {project_id} ({project_name_version})" + '\n')
    log_error_mapping.write("==================================================" + '\n')
    has_error_mapping = False

    classes_from_focal_classes_content: list[str] = []
    for repo in focal_classes_content:
        if repo['project'] == project_name_version:
            classes_from_focal_classes_content = repo['classes']
    
    # print("\n\nList classes_from_focal_classes_content: " + str(len(classes_from_focal_classes_content)))
    # print(classes_from_focal_classes_content)
    # print("")

    project_name_version_without_suffix = project_name_version
    project_name_version_without_suffix = project_name_version_without_suffix.replace("_f", "").replace("_b", "").lower()
    test_and_src_paths = test_and_src_paths_by_project_and_version[project_name_version_without_suffix]
    project_src_path = "" if test_and_src_paths is None else test_and_src_paths["src"]
    if project_src_path is None: # En caso de que project_src_path no contenga 'src'
        project_src_path = ""


    paths_from_focal_classes_content: list[str] = []
    for _class in classes_from_focal_classes_content:
        path_focal_class = _class.rstrip('\n').replace('.', '/')  + '.java'
        basename_from_path = os.path.basename(path_focal_class)
        # Add src_path to focal_class_path
        path_focal_class = os.path.join(project_src_path, path_focal_class)
        # print("basename:" + basename_from_path)
        class_path = get_class_path(root, basename_from_path, path_focal_class)
        if class_path is None:
            continue
        # if sys.platform == "win32" or os.name == "nt":
        class_path = class_path.replace("\\", "/") # For Windows
        paths_from_focal_classes_content.append(class_path)

    # print("\n\nList paths_from_focal_classes_content: " + str(len(paths_from_focal_classes_content)))
    # print(paths_from_focal_classes_content)
    # print("")

    for focal in tqdm(focals, leave=True, desc="Extract info from Focal Classes (" + project_name_version + ")"):
        match_focal_class_to_extract = True
        for _path in paths_from_focal_classes_content:
            if focal in _path:
                match_focal_class_to_extract = True
                break
            #    print("\n\nFocal class find in json: " + str(focal))
            #    print(_path)
            #    print("")
            match_focal_class_to_extract = False

        if not match_focal_class_to_extract:
            continue

        log.write("----------" + '\n')
        log.write("Focal: " + focal + '\n')

        #if index == 0:
        try:
            focal_methods = parse_focal_methods(parser, dependency_parser, parserutils, focal, focals)
            #print("\n\n")
            #print(focal_methods)
            #print("\n\n")

            mapped_focal_methods = get_mapped_focal_methods(project_name_version, focal_methods, focal)
            #print("\n\n")
            #print(mapped_focal_methods)
            #print("\n\n")

            mfm_size = len(mapped_focal_methods)
            tot_mfm += mfm_size
            if mfm_size > 0:
                mfm_by_focal_list.append(mapped_focal_methods)
        except Exception as ex:
            #tb = traceback.format_exc()
            #tb = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            has_error_mapping = True
            error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
            log.write("Error parsing classes: " + str(type(ex).__name__) + ": " + str(ex) + '\n')
            log_error_mapping.write("------------------------------" + '\n')
            log_error_mapping.write("Focal: " + focal + '\n')
            log_error_mapping.write("Error parsing classes: " + str(type(ex).__name__) + ": " + str(ex) + '\n')
            log_error_mapping.write(error_trace + '\n\n\n')
            log_error_mapping.flush()
            log_error_mapping.close()
            raise ex

        index += 1
    
    #Export Mapped Focal Methods
    if len(mfm_by_focal_list) > 0:
        export_mfm(project_name_version, mfm_by_focal_list, output)
        
        if len(paths_from_focal_classes_content) > 0:
            #path_project_name_version = os.path.join(output, project_name_version)
            path_copy_focal_classes = os.path.join(output, "focal_classes")
            os.makedirs(path_copy_focal_classes, exist_ok=True)
            for _path in paths_from_focal_classes_content:
                shutil.copy(_path, path_copy_focal_classes)
    
    #Print Stats
    log.write("\n=============== SUMMARY ===============" + '\n')
    log.write("Total Focal Classes: " + str(tot_fclasses) + '\n')
    log.write("Total Classes with MFM: " + str(len(mfm_by_focal_list)) + '\n')
    log.write("Mapped Focal Methods (MFM): " + str(tot_mfm) + '\n')

    log.close()
    log_error_mapping.close()
    
    if not has_error_mapping:
        os.remove(log_error_mapping_path)

    return tot_fclasses, len(mfm_by_focal_list), tot_mfm, repo_exists, error_finding_java_files

    #parser = ClassParser(language)
    #project_name = os.path.split(root)[1]
    #return parse_all_classes(parser, focals, project_name, output, log)


def parse_focal_methods(parser: ClassParser, dependency_parser: DependencyClassParser, parserutils: DependencyParserUtils, focal_file: str, all_focal_java_files):
    """
    Parse source file and extracts focal methods (non test cases)
    """
    parsed_classes = parser.parse_file(focal_file)
    parsed_classes = parserutils.parse_potential_focal_and_external_dependencies(dependency_parser, parsed_classes, all_focal_java_files)

    focal_methods = list()

    for parsed_class in parsed_classes:
        #parsed_class['project_name_version'] = version

        for parsed_method in parsed_class['methods']:
            method = dict(parsed_method)
            # if (not method['is_testcase'] 
            #         and not method['is_constructor'] 
            #         and not 'private' in method['modifiers']
            #         and not 'protected' in method['modifiers']
            #         and not 'abstract' in method['modifiers']):
            if (not method['is_testcase'] 
                   and not method['is_constructor']
                   and not 'abstract' in method['modifiers']
                   and 'public' in method['modifiers']):
                #Class Info
                focal_class = dict(parsed_class)
                focal_class.pop('argument_list')
                #focal_class.pop('fields') # Aún no se borra esto
                #focal_class.pop('methods') # Aún no se borra esto

                focal_class['file'] = focal_file
                method['class'] = focal_class

                focal_methods.append(method)

    return focal_methods


def get_mapped_focal_methods(project_name_version: str, focal_methods: list, focal_class_file: str):
    mapped_focal_methods = list()
    for focal_method in focal_methods:
        mapped_focal_method = {}
        mapped_focal_method['project_name_version'] = project_name_version
        mapped_focal_method['focal_class'] = focal_class_file
        mapped_focal_method['focal_method'] = focal_method

        mapped_focal_methods.append(mapped_focal_method)
    
    return mapped_focal_methods


def export_mfm(project_name_version, mfm_by_focal_list, output):
    """
    Export a JSON file representing the Mapped Test Case (mtc)
    It contains info on the Test and Focal Class, and Test and Focal method
    """
    mfm_id = 0
    for mfm_by_focal in mfm_by_focal_list:
        for mfm_p in mfm_by_focal:
            mfm = copy.deepcopy(mfm_p)
            mfm['focal_class'] = mfm['focal_method'].pop('class') # Retorna el atributo class que se está borrando del atributo focal_method

            #Clean Focal Class data
            for fmethod in mfm['focal_class']['methods']:
                fmethod.pop('body')
                fmethod.pop('class')
                fmethod.pop('used_private_signatures_of_class')
                fmethod.pop('used_non_private_signatures_of_class')
                fmethod.pop('class_private_deps_used')
                fmethod.pop('class_non_private_deps_used')
                fmethod.pop('signatures_of_external_dependencies')
                fmethod.pop('external_dependencies')

            #print("\n\n")
            #print(mfc)
            #print("\n\n")

            mfm_file = project_name_version + "_" + str(mfm_id) + ".json"
            json_path = os.path.join(output, mfm_file)
            export(mfm, json_path)
            mfm_id += 1


def export(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
    #with open(file_path, 'w') as f:
        #json.dump(dict, f, indent=2) 
        #json.dump(dict, f)
        data_json = json.dumps(data)
        f.write(data_json)



def analyze_project_wrapper(args):
    analyze_project(*args)
    return 1


def analyze_projects(projects_paths: dict[str, list[str]], 
                     focal_classes_content: list[dict], 
                     test_and_src_paths_by_project_and_version: dict[str, dict[str, str]], 
                     output: str, 
                     output_empty: str):
    """
    Analyze a list of projects
    """
    start_time = time.time()
    num_cpus = os.cpu_count() # 8
    print(f'Cantidad de workers: {num_cpus}\n')

    # https://medium.com/@harshit4084/track-your-loop-using-tqdm-7-ways-progress-bars-in-python-make-things-easier-fcbbb9233f24
    # https://tqdm.github.io/docs/tqdm/
    # https://pypi.org/project/tqdm/#ipython-jupyter-integration
    
    for project_id in projects_paths:
        list_paths_by_project = projects_paths[project_id]

        with Pool(num_cpus) as pool:
            with tqdm(total=len(list_paths_by_project), leave=True, desc=f"Analyzing versions of project {project_id}") as pbar:
                # Crea una lista de argumentos para cada llamada a analyze_project
                args_list = [(project_path, project_id, focal_classes_content, test_and_src_paths_by_project_and_version, output, output_empty) for project_path in list_paths_by_project]
                for _ in pool.imap_unordered(analyze_project_wrapper, args_list):
                    pbar.update()


    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_timeformatted = time.strftime("%d days, %H:%M:%S", time.gmtime(elapsed_time))
    print("\n\n\n")
    print(f"Total time seconds: {elapsed_time}")
    print(f"Total time formatted: {elapsed_timeformatted}")


def parse_args():
    """
    Parse the args passed from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repos_path", 
        type=str, 
        default="E:/000_Tesis/000_d4j_revisions",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--project_id",
        type=str,
        #default="all",
        default="all",
        help="ID used to refer to the repo",
    )
    parser.add_argument(
        "--focal_classes_json_file",
        type=str,
        #default="/tmp/output_empty/",
        default="E:/000_Tesis/custom_scripts_d4j/focal_classes.json",
        help="Json file with classes by project version",
    )
    parser.add_argument(
        "--test_and_src_paths_json_file",
        type=str,
        #default="/tmp/output_empty/",
        default="E:/000_Tesis/custom_scripts_d4j/test_and_src_paths_by_project.json",
        help="Json file with test and src paths by project version",
    )
    parser.add_argument(
        "--extract_only_focal_classes",
        type=bool,
        #default="/tmp/output_empty/",
        default=True,
        help="indicates whether to only extract methods from focal classes",
    )
    parser.add_argument(
        "--output",
        type=str,
        #default="/tmp/output/",
        default="E:/000_Tesis/custom_scripts_d4j/output_only_public_and_package/",
        help="Path to the output folder",
    )
    parser.add_argument(
        "--output_empty",
        type=str,
        #default="/tmp/output_empty/",
        default="E:/000_Tesis/custom_scripts_d4j/output_only_public_and_package_empty/",
        help="Path to the empty outputs folder",
    )

    return vars(parser.parse_args())


def main():
    args = parse_args()
    repos_path = args['repos_path']
    project_id = args['project_id']
    extract_only_focal_classes = args['extract_only_focal_classes']
    focal_classes_json_file = args['focal_classes_json_file']
    test_and_src_paths_json_file = args['test_and_src_paths_json_file']
    output = args['output']
    output_empty = args['output_empty']

    list_projects_version_names = []
    focal_classes_content = []
    if extract_only_focal_classes:
        if focal_classes_json_file is None or focal_classes_json_file.strip() == '':
            raise 'If extract_only_focal_classes=True, you must provide a path to the .json file for the focal_classes_json_file variable'
        if not os.path.exists(focal_classes_json_file):
            raise f'Cannot find file {focal_classes_json_file}'
        
        with open(focal_classes_json_file, 'r') as f:
            focal_classes_content = json.load(f)
        list_projects_version_names = [repo['project'] for repo in focal_classes_content]

    test_and_src_paths_by_project_and_version: dict[str, dict[str, str]] = {}
    with open(test_and_src_paths_json_file, 'r') as f:
        test_and_src_paths_by_project_and_version = json.load(f)

    # list_projects_d4j = ['Csv', 'Cli', 'Lang', 'Chart', 'Gson']
    list_projects_d4j = ['Closure', 'Cli', 'Codec', 'Collections', 'Compress', 'Csv', 'JxPath', 'Lang', 'Math', 'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Chart', 'Time', 'Jsoup', 'Mockito']
    
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
    for project_revision in next(os.walk(repos_path))[1]:
        if len(list_projects_version_names) > 0 and project_revision not in list_projects_version_names:
            continue

        path_project = os.path.join(repos_path, project_revision)
        project_name = project_revision.split("_")[0]

        if project_id == 'all' or project_revision.startswith(project_id):
            #if "Gson_1_f" in path_project:
            projects_paths[project_name].append(path_project)
            i += 1
            #projects_paths_list.append(path_project)

    print(f"Total repos to analyze: {str(i)}")
    # print(projects_paths)

    analyze_projects(projects_paths, focal_classes_content, test_and_src_paths_by_project_and_version, output, output_empty)
    
 
if __name__ == '__main__':
    main()