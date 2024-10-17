import argparse
import shutil
import subprocess
import copy
import json
import glob
import stat
import os
import sys
import random
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
from dependency_parser_utils import DependencyParserUtils
import git
from git import RemoteProgress, Repo
from command_runner.elevate import is_admin, elevate


PATH_SCRIPT = os.path.abspath(__file__)
DIR_SCRIPT = os.path.dirname(PATH_SCRIPT)

#export GITHUB_USER=username
#export GITHUB_TOKEN=token
GITHUB_USER = os.environ['GITHUB_USER']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']


def retry(wait, retries=3, reraise=True):
    """ Decorator retries a function if an exception is raised during function
    invocation, to an arbitrary limit.
    :param wait: int, time in seconds to wait to try again
    :param retries: int, number of times to retry function. If None, unlimited
        retries.
    :param reraise: bool, re-raises the last caught exception if true
    """
    def inner(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            tries = 0
            ex = None
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    tries += 1
                    ex = e
                    #print(f"Caught: {str(e)}")
                    #print(f"Sleeping {str(wait)} seconds\n")
                    if tries <= retries or retries is None:
                        time.sleep(wait)
                    else:
                        break
            if reraise and ex is not None:
                raise ex
        return wrapped
    return inner


class CloneProgress(RemoteProgress):
    # https://stackoverflow.com/questions/51045540/python-progress-bar-for-git-clone
    def __init__(self, repo_id):
        super().__init__()
        self.pbar = tqdm(leave=False, desc="Cloning repo_id " + str(repo_id))

    def update(self, op_code, cur_count, max_count=None, message=''):
        #if message:
        #    print(message)
        self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()


@retry(wait=3, retries=3, reraise=True)
def clone_repo(repo_id, repo_git_auth, repo_path) -> Repo:
    # https://gitpython.readthedocs.io/en/stable/reference.html#module-git.repo.base
    # https://git-scm.com/docs/git-clone
    # depth=N: Copia superficial, solo descarga los N commits más recientes (útil para repositorios grandes)
    repo_cloned = git.Repo.clone_from(repo_git_auth, repo_path, depth=1, multi_options=["--shallow-submodules", "--no-tags", "--single-branch"], progress=CloneProgress(repo_id))
    #git.Repo.clone_from(repo_git_auth, repo_path, depth=1, multi_options=["--shallow-submodules", "--no-tags", "--single-branch", "--filter=blob:limit=5m"], progress=CloneProgress(repo_id))
    #git.Repo.clone_from(repo_git_auth, repo_path, depth=1, multi_options=["--filter=blob:none"], progress=CloneProgress(repo_id))
    return repo_cloned


def copy_error_files(path_by_type_error, repo_id, output_empty, dataset_out, files):
    dir_empty_by_type_error = os.path.join(output_empty, path_by_type_error + str(repo_id))
    os.makedirs(dir_empty_by_type_error, exist_ok=True)
    for file in files:
        shutil.copy(os.path.join(dataset_out, file), dir_empty_by_type_error)


def analyze_project(repository: dict, tmp: str, output: str, output_empty: str):
    """
    Analyze a single project
    """
    #os.system("sshpass -p your_password ssh user_name@your_localhost")
    repo_git = repository['url']
    repo_id = repository['repo_id']

    repo = copy.deepcopy(repository)
    repo["url"] = repo_git
    repo["repo_id"] = repo_id
    if 'num_instances' in repo:
        repo.pop('num_instances')

    #Create folders
    os.makedirs(tmp, exist_ok=True)
    #os.chdir(tmp)
    repo_path = os.path.join(tmp, str(repo_id))
    dataset_out = os.path.join(output, str(repo_id))
    os.makedirs(dataset_out, exist_ok=True)

    repo_git_auth = repo_git
    repo_git_auth = repo_git_auth.replace('https://', f'https://{GITHUB_USER}:{GITHUB_TOKEN}@')

    #Clone repo
    print(f"\n\nCloning repository {repo_id} ({repo_git})...")
    #subprocess.call(['git', 'clone', repo_git_auth, repo_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    error_cloning = False
    try:
        repo_cloned = clone_repo(repo_id, repo_git_auth, repo_path)
    except Exception as ex:
        error_cloning = True
        #error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        #print(error_trace)
        # force delete folder with cloning errors
        try:
            shutil.rmtree(repo_path, ignore_errors=True)
            time.sleep(3)
            # force delete empty folders
            if os.path.exists(repo_path):
                os.rmdir(repo_path)
        except Exception as ex:
            shutil.rmtree(repo_path, ignore_errors=True)
            time.sleep(3)
    

    #Run analysis
    language = 'java'
    print(f"Extracting and mapping tests from repo {repo_id} ({repo_git})...")
    tot_mtc = find_map_test_cases(repo_path, language, dataset_out, repo, error_cloning)
    (tot_tclass, tot_tc, tot_tclass_fclass, tot_mtc, repo_exists, repo_has_test_files, error_finding_java_files) = tot_mtc


    if tot_mtc == 0:
        files = os.listdir(dataset_out)

        if not repo_exists:
            copy_error_files("1_repo_not_exists/", repo_id, output_empty, dataset_out, files)
        elif not repo_has_test_files:
            copy_error_files("2_does_not_have_tests/", repo_id, output_empty, dataset_out, files)
        elif error_finding_java_files:
            copy_error_files("3_error_finding_files/", repo_id, output_empty, dataset_out, files)
        else:
            copy_error_files("4_not_matching_tests/", repo_id, output_empty, dataset_out, files)

        shutil.rmtree(dataset_out, ignore_errors=True)

    
    os.chdir(DIR_SCRIPT)
    #Delete
    try:
        if os.path.exists(repo_path):
            git.rmtree(repo_path)
        #shutil.rmtree(repo_path)
    except Exception as ex:
        shutil.rmtree(repo_path, ignore_errors=True)
        print(f"\nError deleting temp folder of repository {repo_git} - Error: {ex}")
        #error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        #print(error_trace)
        #raise ex
    
    #Print Stats
    print(f"\n\n---- Results Repo {repo_id} ({repo_git}) ----")
    if error_cloning:
        print(f"Error cloning repository {repo_git}")
    else:
        print("Test Classes: " + str(tot_tclass))
        print("Mapped Test Classes: " + str(tot_tclass_fclass))
        print("Test Cases: " + str(tot_tc))
        print("Mapped Test Cases: " + str(tot_mtc))
    print()


def find_map_test_cases(root, language, output, repo, error_cloning):
    """
    Finds test cases using @Test annotation
    Maps Test Classes -> Focal Class
    Maps Test Case -> Focal Method
    """
    #Logging
    log_path = os.path.join(output, "log.txt")
    log = open(log_path, "w", encoding="utf-8")
    log.write(f"REPOSITORY {str(repo['repo_id'])} ({str(repo['url'])})" + '\n')
    log.write("==================================================" + '\n')

    repo_exists: bool = True
    repo_has_test_files: bool = True
    error_finding_java_files: bool = False

    #Move to folder when repo was cloned
    if not error_cloning and os.path.exists(root):
        os.chdir(root)
    else:
        #print("Path repo not exists: " + root + '\n')
        log.write("Path repo not exists: " + root + '\n')
        log.close()
        repo_exists = False
        return 0, 0, 0, 0, repo_exists, True, True
    
    #Test Classes
    try:
        result = subprocess.check_output(r'grep -l -r @Test --include \*.java', shell=True)
        #result = subprocess.check_output(r'grep -l -r @Test --include \*\\.java', shell=True)
        tests = result.decode('ascii').splitlines()
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("\nNo se encontraron archivos java que contengan la anotacion @Test")
            repo_has_test_files = False
            log.write("No se encontraron archivos .java que contengan la anotacion @Test" + '\n')
            log.close()
        else:
            print(f"\nCalledProcessError during grep Test classes: {e}")
            error_finding_java_files = True
            error_trace = ''.join(traceback.TracebackException.from_exception(e).format())
            log.write("CalledProcessError during grep Test classes" + '\n')
            log.write(error_trace)
            log.close()
        
        return 0, 0, 0, 0, repo_exists, repo_has_test_files, error_finding_java_files
    except Exception as ex:
        print(f"\nUnknownError during grep: {ex}")
        error_finding_java_files = True
        error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        log.write("UnknownError during grep" + '\n')
        log.write(error_trace)
        log.close()
        return 0, 0, 0, 0, repo_exists, repo_has_test_files, error_finding_java_files
    
    #print("\n\nList tests")
    #print(tests)
    #print("")

    #Java Files
    try:
        #result = subprocess.check_output(['find', '-name', '*.java'], shell=True)
        #all_java = result.decode('ascii').splitlines()

        all_java = glob.glob('**/*.java', recursive=True)
        all_java = [path.replace("\\", "/") for path in all_java] # For Windows

        all_java = [j.replace("./", "") for j in all_java]
    except Exception as ex:
        print("Error during find java files: " + str(ex) + '\n')
        error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
        log.write(error_trace)
        log.write("Error during find java files" + '\n')
        log.close()
        error_finding_java_files = True
        return 0, 0, 0, 0, repo_exists, repo_has_test_files, error_finding_java_files
    
    #print("\n\nList java files")
    #print(java)
    #print("")

    #Potential Focal Classes
    focals = list(set(all_java) - set(tests))
    focals = [f for f in focals if not "src/test" in f]
    focals_norm = [f.lower() for f in focals]

    log.write("Java Files: " + str(len(all_java)) + '\n')
    log.write("Test Classes: " + str(len(tests)) + '\n')
    log.write("Potential Focal Classes: " + str(len(focals)) + '\n')
    log.flush()

    #Matched tests
    mapped_tests = {}

    #Map Test Class -> Focal Class
    log.write("Perfect name matching analysis Test Class -> Focal Class" '\n')
    for test in tests:
        tests_norm = test.lower().replace("/src/test/", "/src/main/")
        #tests_norm = tests_norm.replace("test", "")

        dirs_path = tests_norm.split("/")
        class_name = dirs_path[-1].replace(".java", "")

        length_test_class_name = len(class_name)
        if class_name.endswith("test"):
            class_name = class_name[:length_test_class_name - 4]
        elif class_name.startswith("test"):
            class_name = class_name[4:]

        tests_norm = "/".join(dirs_path[:-1]) + "/" + class_name + ".java"

        if tests_norm in focals_norm:
            index = focals_norm.index(tests_norm)
            focal = focals[index]
            mapped_tests[test] = focal
    
    log.write("Perfect Matches Found: " + str(len(mapped_tests.keys())) + '\n')
    #print("\n\nMap Test Class -> Focal Class")
    #print(mapped_tests)
    #print("")

    #Stats
    tot_tclass = len(tests)
    tot_tclass_fclass = len(mapped_tests)
    tot_tc = 0
    tot_mtc = 0

    #Map Test Case -> Focal Method
    log.write("Mapping test cases:  Test Case -> Focal Method" '\n')
    mtc_list = list()
    
    parser = ClassParser(language)
    dependency_parser = DependencyClassParser(language)
    parserutils = DependencyParserUtils()

    index = 0

    #test_extract_dependencies(parser, dependency_parser, parserutils)
    #return None
    #pbar = tqdm(range(10), desc="myprog", postfix="postfix", ncols=80, total = 100)

    log_error_mapping_path = os.path.join(output, "log_error_mapping.txt")
    log_error_mapping = open(log_error_mapping_path, "w", encoding="utf-8")
    log_error_mapping.write(f"REPOSITORY {str(repo['repo_id'])} ({str(repo['url'])})" + '\n')
    log_error_mapping.write("==================================================" + '\n')
    has_error_mapping = False

    for test, focal in tqdm(mapped_tests.items(), leave=True, desc="Mapping Test-Cases (" + str(repo['repo_id']) + ")"):
        log.write("----------" + '\n')
        log.write("Test: " + test + '\n')
        log.write("Focal: " + focal + '\n')

        #if index == 0:
        try:
            test_cases = parse_test_cases(parser, test)
            focal_methods = parse_potential_focal_methods(parser, dependency_parser, parserutils, focal, focals)
            tot_tc += len(test_cases)
            #print("\n\n")
            #print(focal_methods)
            #print("\n\n")

            #print("\n\n")
            #print(test_cases)
            #print("\n\n")

            mtc = match_test_cases(parserutils, test, focal, test_cases, focal_methods, log)
            #print("\n\n")
            #print(mtc)
            #print("\n\n")

            mtc_size = len(mtc)
            tot_mtc += mtc_size
            if mtc_size > 0:
                mtc_list.append(mtc)
        except Exception as ex:
            #tb = traceback.format_exc()
            #tb = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            has_error_mapping = True
            print(f"Error parsing class {focal} for repo_id {str(repo['repo_id'])}: {str(type(ex).__name__)}: {str(ex)} \n")
            error_trace = ''.join(traceback.TracebackException.from_exception(ex).format())
            log.write("Error parsing classes: " + str(type(ex).__name__) + ": " + str(ex) + '\n')
            log_error_mapping.write("------------------------------" + '\n')
            log_error_mapping.write("Test: " + test + '\n')
            log_error_mapping.write("Focal: " + focal + '\n')
            log_error_mapping.write("Error parsing classes: " + str(type(ex).__name__) + ": " + str(ex) + '\n')
            log_error_mapping.write(error_trace + '\n\n\n')
            # if (isinstance(ex, RecursionError)# Es causado cuando el traverse_type tiene demasiada profundidad
            #         or isinstance(ex, IsADirectoryError)
            #         or isinstance(ex, PermissionError)):
            #     continue

            # raise ex

        index += 1
    

    #Export Mapped Test Cases
    if len(mtc_list) > 0:
        export_mtc(repo, mtc_list, output)
    
    #Print Stats
    log.write("\n=============== SUMMARY ===============" + '\n')
    log.write("Test Classes: " + str(tot_tclass) + '\n')
    log.write("Mapped Test Classes: " + str(tot_tclass_fclass) + '\n')
    log.write("Test Cases: " + str(tot_tc) + '\n')
    log.write("Mapped Test Cases: " + str(tot_mtc) + '\n')

    log.close()
    log_error_mapping.close()

    if not has_error_mapping:
        os.remove(log_error_mapping_path)

    return tot_tclass, tot_tc, tot_tclass_fclass, tot_mtc, repo_exists, repo_has_test_files, error_finding_java_files


def test_extract_dependencies(parser: ClassParser, dependency_parser: DependencyClassParser, parserutils: DependencyParserUtils):
    #text = textwrap.dedent("""
    #                Text bock here
    #                """)
    
    # file_text = R"E:\000_Tesis\project_tesis_build_dataset\ClasePrueba.java"
    # parsed_classe = parser.parse_file(file_text)
    # print(parsed_classe)
    # return ""

    print(os.getcwd())
    #repo_path = os.path.join("java_classes/", "")
    repo_path = R"E:\000_Tesis\project_tesis_build_dataset\000_java_classes_prueba"
    if os.path.exists(repo_path):
        os.chdir(repo_path)
        print(os.getcwd())
    else:
        print("PATH NO EXISTE")
        return 0, 0, 0, 0

    java_files = [
        "src/main/com/eljavatar/focals/FocalContext.java",
        "src/main/com/eljavatar/focals/ExternalContext02.java",
        "src/main/com/eljavatar/focals/ExternalContext03.java",
        "src/main/com/eljavatar/focals/SamePackageExternal01.java",
        "src/main/com/eljavatar/externals/ExternalContext01.java",
        "src/main/com/eljavatar/externals/ExternalContext02.java",
        "src/main/com/eljavatar/externals/ExternalContext03.java",
        "src/main/com/eljavatar/externals/ExternalContext04.java",
        "src/main/com/eljavatar/externals/StaticExternal01.java"
    ]

    focal_file = "src/main/com/eljavatar/focals/FocalContext.java"
    #parsed_classes = parser.parse_file(focal_file)

    #parsed_classes = parse_potential_focal_and_external_dependencies(dependency_parser, parserutils, parsed_classes, java_files)
    #parsed_classes = parserutils.parse_potential_focal_and_external_dependencies(dependency_parser, parsed_classes, java_files)

    #print("\n\n")
    #print(parsed_classes)
    #print("\n\n")

    focal_methods = parse_potential_focal_methods(parser, dependency_parser, parserutils, focal_file, java_files)
    #print("\n\n")
    #print(focal_methods)
    #print("\n\n")

    mapped_test_cases = list()
    for meth in focal_methods:
        mapped_test_case = {}
        mapped_test_case['focal_class'] = focal_file
        mapped_test_case['focal_method'] = meth
        mapped_test_cases.append(mapped_test_case)

    mtc_p_list = []
    for mtc_p in mapped_test_cases:
        mtc = copy.deepcopy(mtc_p)
        mtc['focal_class'] = mtc['focal_method'].pop('class')
        mtc['repository'] = "local_repo_test"

        #Clean Focal Class data
        for fmethod in mtc['focal_class']['methods']:
            fmethod.pop('body')
            fmethod.pop('class')
            fmethod.pop('used_private_signatures_of_class')
            fmethod.pop('used_non_private_signatures_of_class')
            fmethod.pop('class_private_deps_used')
            fmethod.pop('class_non_private_deps_used')
            fmethod.pop('signatures_of_external_dependencies')
            fmethod.pop('external_dependencies')
        
        mtc_p_list.append(mtc)
    
    print("\n\n")
    print(mtc_p_list)
    print("\n\n")

    '''
    _files = [
        "extras/src/main/java/com/google/gson/MyClass1.java",
        "extras/src/main/java/com/google/gson/MyClass2.java",
        "extras/src/main/java/com/google/gson/MyClass3.java",
        "extras/src/main/java/com/google/gson/MyClass4.java",
        "gson/src/main/java/com/google/gson/internal/MyClass1.java",
        "gson/src/main/java/com/google/gson/internal/MyClass2.java"
    ]
    _imports = [
        #"import com.google.gson.MyClass1;",
        #"import com.google.gson.MyClass2;",
        "import com.google.gson.*;",
        "import com.google.gson.internal.MyClass1;",
        "import com.google.gson.internal.MyClass2;",
    ]
    _package = "com/google/gson"
    print("\n\n\n\n")
    _path_imports, _imports_not_in_project = get_path_imports(_imports, _package, "MyClass2", _files)
    print("\n_imports_not_in_project = " + str(_imports_not_in_project))
    print("\n_path_imports = " + str(_path_imports))
    print("\n\n\n\n")
    '''

    return ""



def parse_test_cases(parser: ClassParser, test_file: str):
    """
    Parse source file and extracts test cases
    """
    parsed_classes = parser.parse_file(test_file)

    test_cases = list()
    
    for parsed_class in parsed_classes:
        for method in parsed_class['methods']:
            if method['is_testcase']:

                #Test Class Info
                test_case_class = dict(parsed_class)
                test_case_class.pop('methods')
                test_case_class.pop('argument_list')

                test_case_class['file'] = test_file
                method['class'] = test_case_class

                method.pop('use_some_field')
                method.pop('var_declars')
                method.pop('class_fields_used') # En una proxima version, extraer esta info
                method.pop('class_method_references_used') # En una proxima version, extraer esta info
                method.pop('class_methods_used') # En una proxima version, extraer esta info
                method.pop('used_external_dependencies')
                method.pop('methods_from_external_dependencies')
                method.pop('method_references_from_external_dependencies')
                method.pop('fields_from_external_dependencies')
                #test_case_class.pop('method_dependencies_by_class') # Aún no se borra esto
                #test_case_class.pop('method_references_dependencies_by_class') # Aún no se borra esto
                method.pop('field_dependencies_by_class')
                method.pop('undefined_method_dependencies')
                method.pop('class_methods_that_invoke_other_methods')

                test_cases.append(method)
    
    return test_cases


def parse_potential_focal_methods(parser: ClassParser, dependency_parser: DependencyClassParser, parserutils: DependencyParserUtils, focal_file: str, all_focal_java_files):
    """
    Parse source file and extracts potential focal methods (non test cases)
    """
    parsed_classes = parser.parse_file(focal_file)

    parsed_classes = parserutils.parse_potential_focal_and_external_dependencies(dependency_parser, parsed_classes, all_focal_java_files)

    potential_focal_methods = list()

    for parsed_class in parsed_classes:
        for parsed_method in parsed_class['methods']:
            method = dict(parsed_method)
            if not method['is_testcase']: #and not method['constructor']:

                #Class Info
                focal_class = dict(parsed_class)
                focal_class.pop('argument_list')
                #focal_class.pop('fields') # Aún no se borra esto
                #focal_class.pop('methods') # Aún no se borra esto

                focal_class['file'] = focal_file
                method['class'] = focal_class

                potential_focal_methods.append(method)

    return potential_focal_methods


def match_test_cases(parserutils: DependencyParserUtils, test_class, focal_class, test_cases, focal_methods, log):
    """
    Map Test Case -> Focal Method
    It relies on two heuristics:
    - Name: Focal Method name is equal to Test Case name, except for "test"
    - Unique Method Call: Test Case invokes a single method call within the Focal Class
    """
    #Mapped Test Cases
    mapped_test_cases = list()

    focal_class_name = ""
    for focal_meth in focal_methods:
        focal_class_name = focal_meth['class']['class_name']
        break

    tested_focal_methods = set()

    focals_norm = [f['method_name'].lower() for f in focal_methods]
    for test_case in test_cases:
        #test_case_norm = test_case['method_name'].lower().replace("test", "")
        test_case_norm = test_case['method_name'].lower()

        length_test_case_name = len(test_case_norm)
        if test_case_norm.endswith("test"):
            test_case_norm = test_case_norm[:length_test_case_name - 4]
        elif test_case_norm.startswith("test"):
            test_case_norm = test_case_norm[4:]

        log.write("Test-Case: " + test_case['method_name'] + '\n')

        #Matching Strategies
        if test_case_norm in focals_norm:
            #Name Matching
            index = focals_norm.index(test_case_norm)
            focal = focal_methods[index]

            test_case.pop('method_dependencies_by_class')
            test_case.pop('method_references_dependencies_by_class')

            mapped_test_case = {}
            mapped_test_case['test_class'] = test_class
            mapped_test_case['test_case'] = test_case
            mapped_test_case['focal_class'] = focal_class
            mapped_test_case['focal_method'] = focal

            mapped_test_cases.append(mapped_test_case)
            tested_focal_methods.add(focal['parameters'])
            log.write("> Found Focal-Method: " + focal['parameters'] + '\n')
        
        else:
            #Single method invoked that is in the focal class
            method_references_from_focal_class = list()
            for dependency in test_case['method_references_dependencies_by_class']:
                dep_name = parserutils.get_class_name(dependency)
                if dep_name == focal_class_name:
                    method_references_from_focal_class = test_case['method_references_dependencies_by_class'][dependency]

            method_dependencies_from_focal_class = dict()
            for dependency in test_case['method_dependencies_by_class']:
                dep_name = parserutils.get_class_name(dependency)
                if dep_name == focal_class_name:
                    method_dependencies_from_focal_class = test_case['method_dependencies_by_class'][dependency]

            if (len(method_references_from_focal_class) > 1
                    or len(method_dependencies_from_focal_class) > 1):
                continue

            extract_methods_from_focal_class, _ = parserutils.get_methods_from_external_dependency(
                method_dependencies_from_focal_class, method_references_from_focal_class, focal_methods
            )

            if len(extract_methods_from_focal_class) == 1:
                focal = extract_methods_from_focal_class[0]

                test_case.pop('method_dependencies_by_class')
                test_case.pop('method_references_dependencies_by_class')

                mapped_test_case = {}
                mapped_test_case['test_class'] = test_class
                mapped_test_case['test_case'] = test_case
                mapped_test_case['focal_class'] = focal_class
                mapped_test_case['focal_method'] = focal

                mapped_test_cases.append(mapped_test_case)
                tested_focal_methods.add(focal['parameters'])
                log.write("> [Single-Invocation] Found Focal-Method: " + focal['parameters'] + '\n')

        #test_case.pop('method_dependencies_by_class')
        #test_case.pop('method_references_dependencies_by_class')
                    
    log.write("+++++++++" + '\n')
    log.write("Test-Cases: " + str(len(test_cases)) + '\n')
    log.write("Focal Methods: " + str(len(focals_norm)) + '\n')
    log.write("Tested Focal Methods: " + str(len(tested_focal_methods)) + '\n')
    log.write("Mapped Test Cases: " + str(len(mapped_test_cases)) + '\n')
    return mapped_test_cases


def export_mtc(repo, mtc_list, output):
    """
    Export a JSON file representing the Mapped Test Case (mtc)
    It contains info on the Test and Focal Class, and Test and Focal method
    """
    mtc_id = 0
    for mtc_file in mtc_list:
        for mtc_p in mtc_file:
            mtc = copy.deepcopy(mtc_p)
            mtc['test_class'] = mtc['test_case'].pop('class')
            mtc['focal_class'] = mtc['focal_method'].pop('class')
            mtc['repository'] = repo

            #Clean Focal Class data
            for fmethod in mtc['focal_class']['methods']:
                fmethod.pop('body')
                fmethod.pop('class')
                fmethod.pop('used_private_signatures_of_class')
                fmethod.pop('used_non_private_signatures_of_class')
                fmethod.pop('class_private_deps_used')
                fmethod.pop('class_non_private_deps_used')
                fmethod.pop('signatures_of_external_dependencies')
                fmethod.pop('external_dependencies')

            #print("\n\n")
            #print(mtc)
            #print("\n\n")

            mtc_file = str(repo["repo_id"]) + "_" + str(mtc_id) + ".json"
            json_path = os.path.join(output, mtc_file)
            export(mtc, json_path)
            mtc_id += 1


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


def get_repos_not_exists():
    # Escribe los nombres de las carpetas en un archivo
    #with open('E:/000_Tesis/project_tesis_build_dataset/repos_not_exists.txt', 'r') as archivo:
    with open('/root/repos_not_exists.txt', 'r') as archivo:
        carpetas = archivo.readlines()

    # Elimina los saltos de línea y espacios adicionales
    repos_fix = [carpeta.strip() for carpeta in carpetas]
    print(f'Cantidad de carpetas: {len(repos_fix)}')
    return repos_fix


def analyze_repositories(repositories: list[dict], tmp: str, output: str, output_empty: str):
    """
    Analyze a list of repositories
    """
    start_time = time.time()
    # Convert the repo_lines list to a list of dictionaries
    # Split the repo_lines list into a list of strings

    num_cpus = os.cpu_count() # 8
    #num_cpus = 16
    #num_cpus = num_cpus // 2
    #workers: int = num_cpus // 2
    print(f'Cantidad de workers: {num_cpus}\n')

    repos = []
    #folders = get_repos_not_exists()
    #random.shuffle(folders)
    #folders = ["32538871"]
    #print(repositories[0])
    for repo in repositories:
        #if str(repo['repo_id']) in folders:
        repos.append(repo)
    
    print(f"count repos to analyze: {len(repos)}")

    # https://medium.com/@harshit4084/track-your-loop-using-tqdm-7-ways-progress-bars-in-python-make-things-easier-fcbbb9233f24
    # https://tqdm.github.io/docs/tqdm/
    # https://pypi.org/project/tqdm/#ipython-jupyter-integration
    
    # with tqdm(total=len(repos), leave=True, desc="Analyzing projects") as pbar:
    #     partial_func = partial(analyze_project, tmp=tmp, output=output, output_empty=output_empty)
    #     for repo in repos:
    #         partial_func(repository=repo)
    #         pbar.update(1)
    
    
    with Pool(num_cpus) as pool:
        with tqdm(total=len(repos), leave=True, desc="Analyzing projects") as pbar:
            # Crea una lista de argumentos para cada llamada a analyze_project
            args_list = [(repo, tmp, output, output_empty) for repo in repos]
            #pool.map(analyze_project_wrapper, args_list)
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
        "--repos_file", 
        type=str, 
        #default="E:/000_Tesis/project_tesis_build_dataset/repos_prueba.json",
        #default="E:/000_Tesis/project_tesis_build_dataset/repos/test.json",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--repo_url", 
        type=str, 
        #default="https://github.com/openhab/openhab-core",
        default="https://github.com/google/gson",
        #default="https://github.com/uber/marmaray",
        help="GitHub URL of the repo to analyze",
    )
    parser.add_argument(
        "--repo_id",
        type=str,
        #default="48337670",
        default="32538871",
        #default="116403104",
        help="ID used to refer to the repo",
    )
    parser.add_argument(
        "--tmp",
        type=str,
        #default="/tmp/tmp/",
        default="E:/000_Tesis/project_tesis_build_dataset/tmp/",
        help="Path to a temporary folder used for processing",
    )
    parser.add_argument(
        "--output",
        type=str,
        #default="/tmp/output/",
        default="E:/000_Tesis/project_tesis_build_dataset/output/",
        help="Path to the output folder",
    )
    parser.add_argument(
        "--output_empty",
        type=str,
        #default="/tmp/output_empty/",
        default="E:/000_Tesis/project_tesis_build_dataset/output_empty/",
        help="Path to the empty outputs folder",
    )

    return vars(parser.parse_args())

def main():
    args = parse_args()
    repos_file = args['repos_file']
    repo_git = args['repo_url']
    repo_id = args['repo_id']
    tmp = args['tmp']
    output = args['output']
    output_empty = args['output_empty']

    if repos_file is not None:
        data = []
        with open(repos_file) as f:
            data = json.load(f)
        analyze_repositories(data, tmp, output, output_empty)
    else:
        repo = {
            'repo_id': repo_id,
            'url': repo_git
        }
        analyze_project(repo, tmp, output, output_empty)

    
if __name__ == '__main__':
    print("is_admin: ", is_admin())
    #elevate(main)
    main()


