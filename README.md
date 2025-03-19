# DynaMTests: **Dyna**mic context **M**apped **Tests**

## Description

We present **DynaMTests**: a supervised dataset consisting of Test Cases and their corresponding Focal Methods together with their dynamic context (methods and fields used within the focal method, both from the focal class as well as from external classes) from a large set of Java software repositories. To build DynaMTests, we follow the following process:

1. We analyze Java projects to obtain classes and methods with their associated metadata.

2. We identify each test class and its corresponding focal class.

3. For each test case within a test class, we map it to the related focal method and obtain a set of mapped test cases. We do this as follows:
   
   1. We identify as test case all the methods within a test class that have the @Test annotation (we identify as test class, all those classes that within their code have the `@Test` annotation).
   
   2. We identify the focal method for a specific test case through the following heuristics:
      1. *Class Name Matching*: we look for classes that have the same name as the test class, but without the prefix or suffix Test.
      2. *Method Name Matching*: Within the focal class identified in the previous step, we look for the methods that have the same name as the test method but without the prefix or suffix Test.
      3. *Unique Method Call*: If with the previous heuristic we do not obtain a result, we obtain the methods of the focal class previously identified that are invoked from the test method, and in case we obtain only one method, we select it as the focal method.

4. For each focal method, we associate a metadata representing its dynamic context.


## Accessing via Git LFS

The repository makes use of the Git large file storage (LFS) service. Git LFS does replacing large files in the repository with tiny pointer files. To pull the actual files do:

```shell
# first, clone the repo
git clone git@github.com:eljavatar/DynaMTests.git
# next, change to the DynaMTests folder
cd DynaMTests
# finally, pull the files
git lfs pull
```


## Data Format

The data is organized as dataset and corpus.

### Dataset

The dataset contains test cases mapped to their corresponding focal methods, along with a rich set of metadata. The dataset is stored as JSON files of the following format:

```yaml
repository: repository info
    repo_id: int, unique identifier of the repository in the dataset
    url: string, repository URL
    language: string, programming languages of the repository
    is_fork: Boolean, whether repository is a fork
    fork_count: int, number of forks
    stargazer_count: int, cumulative number of start on GitHub

focal_class: properties of the focal class
    class_name: string, class name
    superclass: string, superclass definition
    interfaces: string, interface definition
    class_signature: string, full class signature definition
    class_modifier: string, class modifiers
    has_constructor: boolean, whether the class has some defined constructor
    fields: list, class fields
    methods: list, class methods
    imports: list, class imports
    package: string, package to which the class belongs
    file: string, relative path (inside the repository) to file containing the focal class

focal_method: properties of the focal method
    method_name: string, focal method name 
    parameters: string, name method with parameter types list of the focal method
    parameters_list: list, parameter types list of the focal method
    modifiers: string, method modifiers
    return: string, return type
    body: string, source code of the focal method
    signature: string, focal method signature (return type + name + parameters)
    full_signature: string, focal method signature (modified + return type + name + parameters)
    full_signature_parameters: string, focal method signature (modified + return type + name + type parameters)
    class_method_signature: string, focal method signature (class + name + parameters)
    is_testcase: boolean, whether the method is a test case
    test_use_mockito: boolean, whether the method use mockito API
    is_constructor: boolean, whether the method is a constructor
    is_get_or_set: boolean, whether the method is a getter o setter
    class_private_deps_used: object with list of private fields and methods used from focal method
    class_non_private_deps_used: object with list of non private fields and methods used from focal method
    external_dependencies: list of external classes used from the focal method (each with the respective list of fields and methods invoked from the focal method)

test_class:  properties of the test class containing the test case
    class_name: string, class name
    superclass: string, superclass definition
    interfaces: string, interface definition
    class_signature: string, full class signature definition
    class_modifier: string, class modifiers
    has_constructor: boolean, whether the class has some defined constructor
    fields: list, class fields
    imports: list, class imports
    package: string, package to which the class belongs
    file: string, relative path (inside the repository) to file containing the test class

test_case: properties of the unit test case
    method_name: string, unit test case method name
    parameters: string, name method with parameter types list of the test case method
    parameters_list: list, parameter types list of the test case method
    modifiers: string, method modifiers
    return: string, return type
    body: string, source code of the focal method
    signature: string, focal method signature (return type + name + parameters)
    full_signature: string, focal method signature (modified + return type + name + parameters)
    full_signature_parameters: string, focal method signature (modified + return type + name + type parameters)
    class_method_signature: string, focal method signature (class + name + parameters)
    is_testcase: boolean, whether the method is a test case
    test_use_mockito: boolean, whether the method use mockito API
    is_constructor: boolean, whether the method is a constructor
    is_get_or_set: boolean, whether the method is a getter o setter
```

### Corpus

The corpus folder contains the parallel corpus of focal methods and test cases, as json, raw, and csv, suitable for training and evaluation of the model.

The corpus is organized into two types of context: focal context (*fm_fc_ms_ff*) (similar to the approach used in [Methods2Test](https://arxiv.org/abs/2203.12776 "Methods2Test arXiv paper")) and dynamic context (*fm_fc_dctx*), which is the approach we propose. The information included in each type of context is as follows:

- **FM_FC_DCTX**: focal method + focal class name + constructor signatures + signatures of focal methods used (private and non-private) + focal class fields used + (private and non-private) + [for each external class used: {external class name + constructor signatures + signatures of external methods used + external class fields used}]

- **FM_FC_MS_FF**: focal method + focal class name + constructor signatures + public method signatures + public fields



## Statistics

A total of 91,385 unique repositories were analyzed, from which 904,870 test cases mapped to their corresponding focal method (and their dynamic context) were obtained in the first instance. However, 2 purging processes were performed in order to obtain the dataset and subsequently the corpus:

1. To obtain the dataset, duplicate `test_case-focal_method` pairs were removed from mined repositories ([Dataset creation](#dataset-creation)).
2. To obtain the corpus, the previously purged dataset was subjected to several normalization processes (e.g., removing code comments, removing line breaks, etc.) and those with syntax errors, those without a body in the test case, those with the `@Ignored` annotation and those that were duplicated in our corpus generated for the [Defects4J](https://github.com/rjust/defects4j "Defects4J GitHub Repo") dataset projects were removed ([Corpus creation](#corpus-creation)).

### Dataset statistics

The dataset contains 790,490 test cases mapped to their corresponding focal method (and their dynamic context), extracted from 9,351 unique repositories (of the total 91,385 repositories analyzed). The dataset is divided into training (~82%), validation (~8.6%) and test (~9.4%) sets:

| Set           | Repositories  | Mapped TestCases |
| :------------ | ------------: | ------------:    |
| Train         | 7,407         | 652,308          |
| Validation    | 923           | 68,102           |
| Test          | 1,021         | 74,716           |
| **Total**     | **9,351**     | **795,126**      |

### Corpus statistics

The corpus contains 772,140 test cases mapped to their corresponding focal method (and their dynamic context), and like the dataset, is divided into training (~81.8 %), validation (~8.7 %) and test (~9.5 %) sets:

| Set           | Repositories  | Mapped TestCases |
| :------------ | ------------: | ------------:    |
| Train         | 7,407         | 631,540          |
| Validation    | 923           | 67,201           |
| Test          | 1,021         | 73,399           |
| **Total**     | **9,351**     | **772,140**      |



## How to replicate the Dataset and Corpus Building process?

### Required dependencies

- Python >= 3.9
- Git >= 2.34

```shell
# Python dependencies
pip install pandas
pip install scikit-learn
pip install packaging
pip install command-runner
pip install GitPython
pip install tree-sitter==0.21.0
pip install tree-sitter-java==0.21.0
```

### GitHub repository list

To perform the mining and data extraction process, a `json` file containing the list of GitHub repositories to be analyzed is required. This json file must have the following structure:

```json
[
    {
        "repo_id": 32538871, // github repository identifier
        "url": "https://github.com/google/gson" // github repository url
    }
    {
        // Another github repository
    }
]
```

You can have more attributes per repository, however, the minimum data required to be able to perform the minaodo are the `repo_id` and `url` attributes. You can use the `repos_prueba.json` file to perform a quick test.

The files used to build our dataset were `repos/train.json`, `repos/validation.json` and `repos/test.json`. However, it is likely that using those same repository lists would not yield the same dataset as ours, due to reasons such as the following:

- The repository was modified
- The repository is no longer publicly accessible
- The repository makes use of the Git large file storage (LFS) service and has exceeded storage capacity
- The repository was removed


### Environment variables

To run the script, the following environment variables are required:

```shell
export GITHUB_USER=your_github_user
export GITHUB_TOKEN=your_github_personal_access_token
```

Some repositories require authentication to be cloned, therefore, to generate the authentication token you must follow the process explained in the official Github documentation: [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).


### Extraction and analysis of repositories

To perform the process of data extraction and analysis of the repositories, the following script is executed to which the json file containing the list of repositories with the format indicated in section [GitHub repository list](#github-repository-list) must be passed as a parameter. For this example we use the file `repos_prueba.json`:

```shell
python find_map_tests_cases_from_repo.py \
	--repos_file "repos_prueba.json" \
	--tmp "/tmp/tmp_repos/" \
	--output "/mining_results/train/output" \
	--output_empty "/mining_results/train/output_empty"
```

The execution of this script results in 2 folders:

- **../output**: In this folder will be stored the test cases mapped to their corresponding focal methods, and grouped by repository, in such a way that for each repository a folder is created where the name will be the value of `repo_id` found in the json file passed through the `repos_file` parameter.

- **../output_empty**: When the mining process is performed it is possible that for many repositories it has not been possible to extract test cases together with their corresponding focal methods for various reasons, therefore, within the output_empty folder the following subfolders are created:

  - *1_repo_not_exists*: List of repositories that could not be cloned (either for one of the reasons explained in the [GitHub repository list](#github-repository-list) section or because there was a connection problem when cloning).
  - *2_does_not_have_tests*: List of repositories that do not have test methods, i.e., those in which no classes were found that had the `@Test` annotation in their code.
  - *3_error_finding_files*: List of repositories from which it is not possible to obtain the list of Java classes.
  - *4_not_matching_tests*: List of repositories from which it was not possible to map test cases to some focal method using the heuristics mentioned in section [Description](#description).

  If during the execution of the script there are connection problems, or if at the end of the execution there are few repositories in the *../output* folder and many repositories in the *../output_empty/1_repo_not_exists* folder, it could be convenient to run it again but only with the list of repositories that are in the *../output_empty/1_repo_not_exists* folder.


### Dataset creation

The dataset creation is performed from the mined repositories and consists of removing duplicate `test_case-focal_method` pairs. To run the script shown below, it is required that the folder passed in the `mining_input` parameter (which in this case is */mining_results*) has at least one (preferably all) of the following subfolders:

- /mining_results/train/output
- /mining_results/validation/output
- /mining_results/test/output

```shell
python clean_duplicates_and_build_dataset.py \
	--mining_input "/mining_results" \
	--output_dataset "/dataset"
```

If the three subfolders *train*, *validation* and *test* exist in the /mining_results folder, the script will start by removing the duplicate `test_case-focal_method` pairs from the test subset, then remove the duplicates from the validation subset (also remove them if they were already added to the train subset) and finally remove the duplicates from the test subset (also remove them if they were already added to the train or validation subset). In this way, 3 subfolders would be generated inside the */dataset* folder, one for each data subset.

If only one of the above mentioned subfolders exists in the /mining_results folder, for example *train*, the script will only remove the duplicates of this dataset, thus creating the */dataset/train* subfolder. Therefore, at this point a data splitting process should be performed in such a way that the other two data subsets and their respective folders */dataset/validation* and */dataset/test* are created.


### Corpus creation

The creation of the corpus consists of two steps.

The first step consists of parsing the repositories of the previously created dataset, in order to obtain data in the form `source-target` (this is the format that a Sequence-to-Sequence language model would use) where `target` would be the test method and `source` would be the focal method together with its respective context, either focal or dynamic (see [Corpus](#corpus) section).

This process would result in the creation of the corpus files in *json* and *raw* format:

```shell
python build_corpus.py \
	--type_dataset "test" \
	--input_dataset "/dataset/test" \
	--input_encoding "utf-8" \
	--output_corpus "/corpus/"

python build_corpus.py \
	--type_dataset "validation" \
	--input_dataset "/dataset/validation" \
	--input_encoding "utf-8" \
	--output_corpus "/corpus/"

python build_corpus.py \
	--type_dataset "train" \
	--input_dataset "/dataset/train" \
	--input_encoding "utf-8" \
	--output_corpus "/corpus/"
```

In case the mining process was carried out on a Windows system, the `input_encoding` parameter should probably be `cp1252`.

The second step consists in creating the corpus files in *csv* format, which is done from the corpus in json format:

```shell
python convert_json_corpus_to_csv_input.py \
	--type_corpus "test" \
	--input_json_corpus "/corpus/json" \
	--input_encoding "utf-8" \
	--output_csv_corpus "/corpus/csv"

python convert_json_corpus_to_csv_input.py \
	--type_corpus "validation" \
	--input_json_corpus "/corpus/json" \
	--input_encoding "utf-8" \
	--output_csv_corpus "/corpus/csv"

python convert_json_corpus_to_csv_input.py \
	--type_corpus "train" \
	--input_json_corpus "/corpus/json" \
	--input_encoding "utf-8" \
	--output_csv_corpus "/corpus/csv"
```




