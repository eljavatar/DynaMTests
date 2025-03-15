# Convert files json to CSV
import argparse
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import os, json, time

SEED = 42

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


def convert(type_corpus: str, corpus_path: str, corpus_csv_out: str):
    os.makedirs(corpus_csv_out, exist_ok=True)
    out_path = os.path.join(corpus_csv_out, type_corpus + ".csv")

    json_files = []

    total_repos = get_total_repos(corpus_path)
    print(f"Total repos {type_corpus}: {str(total_repos)}")

    with tqdm(total=total_repos, desc="Getting json corpus files from folders") as pbar:
        index = 0
        for path in Path(corpus_path).iterdir():
            if path.is_dir():
                json_files.extend([str(path) + '/' + file_json for file_json in os.listdir(path) if file_json.endswith('.json')])
            pbar.update()
            #index = len(json_files)
            #if index > 700:
            #    break

    # import static net.floodlightcontroller.devicemanager.internal.
    # DeviceManagerImpl.DeviceUpdate.Change

    print("JSON files extracted: " + str(len(json_files)))
    #print(json_files[0])
    print()

    #print("Getting dataframe...")
    #tqdm.pandas() #this is how you activate the pandas features in tqdm
    #df = pd.concat([pd.DataFrame([pd.read_json(f_name, typ='series')]) for f_name in json_files]).progress_apply(lambda x: x)

    json_data = []
    i = 0
    for file in tqdm(json_files, desc="Getting json data"):
        df_json = pd.read_json(file, typ='series', orient='records')
        json_data.append(df_json)

        # with open(file) as f:
        #     data = json.load(f)
        #     json_data.append(data)

        # i += 1
        # if i == 10:
        #     break
        
    #print(json_data)
    
    print("\nGetting dataframe...")
    df = pd.DataFrame(json_data)
    #df = pd.json_normalize(json_data)

    # view the concatenated dataframe
    # print(df)
    print()
    print(df.head())
    print(df.columns)
    print()

    ## Columns:
    # target
    # src_fm_fc_ms_ff
    # src_fm_fc_dctx
    # src_fm_fc_dctx_priv
    # imports_focal_class
    # imports_test_class

    print()
    print(df.iloc[:1,0])
    print()
    print(df.iloc[:1,1])
    print()
    print(df.iloc[:1,2])
    print()
    print(df.iloc[:1,3])
    print()
    print(df.iloc[:1,4])
    print()
    print(df.iloc[:1,5])
    print()

    #return
    # df.rename(columns = {'src_fm_fc_ms_ff':'source'}, inplace = True)
    # df.rename(columns = {'s':'source'}, inplace = True)

    # Reordenamos aleatoriamente el DataFrame antes de guardarlo en el CSV
    print("Suffling dataframe...")
    df_shuffled = df.sample(frac=1, random_state=SEED).reset_index(drop=True)

    # convert dataframe to csv file
    print("Converting to CSV...")
    df_shuffled.to_csv(out_path, index=False, encoding="utf-8")

    print("Finish writting CSV")

    # load the resultant csv file
    result = pd.read_csv(out_path)

    # and view the data
    print(result.info())
    #print(result)


def parse_args():
    """
    Parse the args passed from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_json_corpus", 
        type=str,
        default="E:/000_Tesis/project_tesis_build_dataset/corpus/json",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--input_encoding", 
        type=str, 
        default="cp1252",
        #default="utf-8",
        help="Filepath of the json file with the repositories",
    )
    parser.add_argument(
        "--type_corpus",
        type=str,
        default="validation",
        help="Type of dataset to which the corpus will be generated",
    )
    parser.add_argument(
        "--output_csv_corpus",
        type=str,
        default="E:/000_Tesis/project_tesis_build_dataset/corpus/csv/",
        help="Path to the output folder",
    )

    return vars(parser.parse_args())


def main():
    args = parse_args()
    type_corpus = args['type_corpus']
    input_json_corpus = args['input_json_corpus']
    output_csv_corpus = args['output_csv_corpus']

    corpus_input_path = os.path.join(input_json_corpus, type_corpus)

    start_time = time.time()

    convert(type_corpus, corpus_input_path, output_csv_corpus)

    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_timeformatted = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    print("\n\n\n")
    print(f"Total time seconds: {elapsed_time}")
    print(f"Total time formatted: {elapsed_timeformatted}")


if __name__ == '__main__':
    main()