import os
import argparse
import json
import shutil
import time
from tqdm import tqdm


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
        
        #if count_repos >= 5:
        #    break
    
    return count_repos


def extract_uniques(unique_all_tests: set, path_in: str, path_out: str):
    total_repos = get_total_repos(path_in)
    print(f"Total repos in mining results {path_in}: {str(total_repos)}")

    accepted_tests = 0
    ignored_tests = 0

    index_repo = 1
    for repo_folder in next(os.walk(path_in))[1]:
        path_mining_repo = os.path.join(path_in, repo_folder)
        path_dataset_repo = os.path.join(path_out, str(repo_folder))
        #os.makedirs(path_dataset_repo, exist_ok=True)

        message = f"Building json dataset repository {repo_folder} - (Nro. repo: {str(index_repo)} of {str(total_repos)})"
        for file in tqdm(os.listdir(path_mining_repo), desc=message):
            if file.endswith('.json'):
                path_json_file_mining = os.path.join(path_mining_repo, file)

                with open(path_json_file_mining) as f:
                    data = json.load(f)

                    test_case = data['test_case']
                    test_src_code = test_case['body']

                if test_src_code is None or test_src_code in unique_all_tests:
                    ignored_tests += 1
                    continue

                os.makedirs(path_dataset_repo, exist_ok=True)
                unique_all_tests.add(test_src_code)

                shutil.copy(path_json_file_mining, path_dataset_repo)
                accepted_tests += 1
        
        #if index_repo >= 5:
        #    break
        index_repo += 1
    
    return accepted_tests, ignored_tests


def clean_duplicates(path_input: str, path_output: str):
    path_input_train = os.path.join(path_input, "train/output")
    path_input_validation = os.path.join(path_input, "validation/output")
    path_input_test = os.path.join(path_input, "test/output")

    path_output_train = os.path.join(path_output, "train")
    path_output_validation = os.path.join(path_output, "validation")
    path_output_test = os.path.join(path_output, "test")

    os.makedirs(path_output_train, exist_ok=True)
    os.makedirs(path_output_validation, exist_ok=True)
    os.makedirs(path_output_test, exist_ok=True)

    unique_all_tests = set()

    unique_train, ignored_train = extract_uniques(unique_all_tests, path_input_train, path_output_train)
    print("\n\n")
    unique_validation, ignored_validation = extract_uniques(unique_all_tests, path_input_validation, path_output_validation)
    print("\n\n")
    unique_test, ignored_test = extract_uniques(unique_all_tests, path_input_test, path_output_test)
    print("\n\n")

    print(f"Total unique tests: {str(len(unique_all_tests))}")
    print(f"Accepted / Ignored tests Train: {str(unique_train)} / {str(ignored_train)}")
    print(f"Accepted / Ignored tests Validation: {str(unique_validation)} / {str(ignored_validation)}")
    print(f"Accepted / Ignored tests Test: {str(unique_test)} / {str(ignored_test)}")


def parse_args():
    """
    Parse the args passed from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mining_input", 
        type=str, 
        #default="E:/000_Tesis/project_tesis_build_dataset/output",
        default="E:/000_Tesis/project_tesis_build_dataset/mining_results",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--output_dataset",
        type=str,
        default="E:/000_Tesis/project_tesis_build_dataset/dataset",
        help="Path to the output folder",
    )

    return vars(parser.parse_args())


def main():
    args = parse_args()
    mining_input = args['mining_input']
    output_dataset = args['output_dataset']
    
    start_time = time.time()
    clean_duplicates(mining_input, output_dataset)
    end_time = time.time()

    elapsed_time = end_time - start_time
    elapsed_timeformatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    print("\n\n\n")
    print(f"Total time seconds: {elapsed_time}")
    print(f"Total time formatted: {elapsed_timeformatted}")


if __name__ == '__main__':
    main()
    

