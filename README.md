# DynaMTests: Dynamic context Mapped Tests

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

1. To obtain the dataset, duplicate `test_case-focal_method` pairs were removed from mined repositories.
2. To obtain the corpus, the previously purged dataset was subjected to several normalization processes (e.g., removing code comments, removing line breaks, etc.) and those with syntax errors, those without a body in the test case, those with the `@Ignored` annotation and those that were duplicated in our corpus generated for the [Defects4J](https://github.com/rjust/defects4j "Defects4J GitHub Repo") dataset projects were removed.

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


