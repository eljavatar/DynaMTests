import argparse
import copy
import csv
import json
import os
import pandas as pd
import time
from distutils.util import strtobool
from tqdm import tqdm
from transformers import AutoTokenizer, T5Config


# SEED = 42
csv.field_size_limit(10**6) # Limite por defecto por campo: 131072, Lo aumentamos a 1 MB
# random.seed(SEED)

max_length = 1024
parserUtils = None
tokenizer = None


def analize_count_tokens(path_input_corpus: str, corpus_file: str, analyzing_d4j_corpus: bool) -> dict[str, dict[str, int]]:
    corpus_file_name = corpus_file + '_methods.csv' if analyzing_d4j_corpus else corpus_file + '.csv'
    path_corpus_csv = os.path.join(path_input_corpus, corpus_file_name)

    print(f"\nReading file {corpus_file}...")
    df = pd.read_csv(path_corpus_csv)
    df.replace({pd.NA: None}, inplace=True) # Reemplaza los NaN de pandas por None

    list_corpus = df.to_dict(orient='records')
    total_rows = len(list_corpus)

    ## Columns:
    # target
    # src_fm_fc_ms_ff
    # src_fm_fc_dctx
    # src_fm_fc_dctx_priv
    # imports_focal_class
    # imports_test_class

    dict_counts: dict[str, int] = {
        'less_than_or_equal_512': 0,
        'in_range_512_and_1024': 0,
        'in_range_1024_and_2048': 0,
        'greater_than_2048': 0
    }

    counts_by_input_type: dict[str, dict[str, int]] = {
        'target': copy.deepcopy(dict_counts),
        'src_fm_fc_ms_ff': copy.deepcopy(dict_counts),
        'src_fm_fc_dctx': copy.deepcopy(dict_counts),
        'src_fm_fc_dctx_priv': copy.deepcopy(dict_counts),
    }

    for row in tqdm(list_corpus, desc=f"Reading lines of corpus {corpus_file}"):
        if not analyzing_d4j_corpus:
            target = row['target']
        
        src_fm_fc_ms_ff = row['src_fm_fc_ms_ff']
        src_fm_fc_dctx = row['src_fm_fc_dctx']
        src_fm_fc_dctx_priv = row['src_fm_fc_dctx_priv']

        if not analyzing_d4j_corpus:
            analize_using_tokenizer(target, 'target', counts_by_input_type)
        
        analize_using_tokenizer(src_fm_fc_ms_ff, 'src_fm_fc_ms_ff', counts_by_input_type)
        analize_using_tokenizer(src_fm_fc_dctx, 'src_fm_fc_dctx', counts_by_input_type)
        analize_using_tokenizer(src_fm_fc_dctx_priv, 'src_fm_fc_dctx_priv', counts_by_input_type)
    
    if analyzing_d4j_corpus:
        counts_by_input_type.pop('target')
    
    return total_rows, counts_by_input_type


def analize_using_tokenizer(input: str, input_key: str, counts_by_input_type: dict[str, dict[str, int]]):
    tokenized_input = tokenizer(input, return_attention_mask=False, add_special_tokens=False)
    input_length = len(tokenized_input['input_ids'])

    dict_counts: dict[str, int] = counts_by_input_type[input_key]

    if input_length <= 512:
        dict_counts['less_than_or_equal_512'] = dict_counts['less_than_or_equal_512'] + 1
        # return True, False, False, False
    elif input_length > 512 and input_length <= 1024:
        dict_counts['in_range_512_and_1024'] = dict_counts['in_range_512_and_1024'] + 1
        # return False, True, False, False
    elif input_length > 1024 and input_length <= 2048:
        dict_counts['in_range_1024_and_2048'] = dict_counts['in_range_1024_and_2048'] + 1
        # return False, False, True, False
    else: # 2048
        dict_counts['greater_than_2048'] = dict_counts['greater_than_2048'] + 1
        # return False, False, False, True
    
    counts_by_input_type[input_key] = copy.deepcopy(dict_counts)


def export_results_json(data, file_path: str):
    """
    Exports data as json file
    """
    if os.path.exists(file_path):
        os.remove(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        data_json = json.dumps(data, indent = 4)
        f.write(data_json)


def parse_args():
    """
    Parse the args passed from the command line
    """
    #file_path = R"E:\000_Tesis\a3test_atlas_files\eval.tsv"
    #file_out = "validation.txt"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path_all_csv_corpus", 
        type=str, 
        # default="/DynaMTests_project/corpus/csv",
        default="/defects4j_with_dynamtests/corpus_only_public/csv",
        help="Filepath of the all csv files (Train, Valid and Test)",
    )
    parser.add_argument(
        "--corpus_type", 
        type=str, 
        default="all",
        help="Corpus File to analize (train, validation, test, all)",
    )
    parser.add_argument(
        "--analyzing_d4j_corpus", 
        type=lambda x: bool(strtobool(x)), 
        default=True,
        help="Weather if corpus to analyze is from d4j projects",
    )
    parser.add_argument(
        "--output_file", 
        type=str, 
        # default="/DynaMTests_project/corpus/corpus_token_analysis.json",
        default="/defects4j_with_dynamtests/corpus_only_public/corpus_token_analysis.json",
        help="Filepath of de json file output",
    )
    parser.add_argument(
        "--encoding", 
        type=str, 
        default="utf-8",
        help="Encoding of input and output",
    )
    parser.add_argument(
        "--model_base", 
        type=str, 
        default="Salesforce/codet5p-220m",
        help="Model base for autotokenizer",
    )
    parser.add_argument(
        "--cacheDirHuggingFace", 
        type=str, 
        default="/huggingface_models/",
        help="Model base for autotokenizer",
    )
    return vars(parser.parse_args())


if __name__ == '__main__':
    args = parse_args()
    path_all_csv_corpus = args['path_all_csv_corpus']
    corpus_type = args['corpus_type']
    analyzing_d4j_corpus = args['analyzing_d4j_corpus']
    output_file = args['output_file']
    encoding = args['encoding']
    model_base = args['model_base']
    cache_dir_hf = args['cacheDirHuggingFace']

    print("Loading Tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_base, cache_dir=cache_dir_hf)
    tokenizer.model_max_length = max_length
    print("Max length tokenizer: " + str(tokenizer.model_max_length))

    if analyzing_d4j_corpus:
        all_corpus_files = ['Closure', 'Cli', 'Codec', 'Collections', 'Compress', 'Csv', 'JxPath', 'Lang', 'Math', 'Gson', 'JacksonCore', 'JacksonDatabind', 'JacksonXml', 'Chart', 'Time', 'Jsoup', 'Mockito']
    else:
        all_corpus_files = ['train', 'validation', 'test']

    results_by_corpus: dict[str, dict[str, dict[str, int]]] = {}
    totals_by_corpus: dict[str, int] = {}
    results_to_save = {}

    start_time = time.time()

    if corpus_type == 'all':
        for corpus in all_corpus_files:
            total_rows, counts_by_input_type = analize_count_tokens(path_all_csv_corpus, corpus, analyzing_d4j_corpus)
            results_by_corpus[corpus] = counts_by_input_type
            totals_by_corpus[corpus] = total_rows
            results_to_save[corpus] = {
                'total_rows': total_rows,
                'counts_by_input_type': counts_by_input_type
            }
    else:
        total_rows, counts_by_input_type = analize_count_tokens(path_all_csv_corpus, corpus_type, analyzing_d4j_corpus)
        results_by_corpus[corpus_type] = counts_by_input_type
        totals_by_corpus[corpus_type] = total_rows
        results_to_save[corpus_type] = {
            'total_rows': total_rows,
            'counts_by_input_type': counts_by_input_type
        }
    
    # dict_counts: dict[str, int] = {
    #     'less_than_or_equal_512': 0,
    #     'in_range_512_and_1024': 0,
    #     'in_range_1024_and_2048': 0,
    #     'greater_than_2048': 0
    # }
    for corpus, counts_by_input_type in results_by_corpus.items():
        total_rows_corpus = totals_by_corpus[corpus]
        print(f"\n\n\nCorpus: {corpus} - Rows: {total_rows_corpus}")

        for input_type, dict_counts in counts_by_input_type.items():
            print(f"\nInput type: {input_type}")

            for key, count in dict_counts.items():
                print(f"{key}: {count}")
    
    print("\n")


    export_results_json(results_to_save, output_file)


    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_timeformatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    print("\n\n")
    print(f"Total time seconds: {elapsed_time}")
    print(f"Total time formatted: {elapsed_timeformatted}\n")
