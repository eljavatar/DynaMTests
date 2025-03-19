#!/usr/bin/env bash

repos=(Closure Cli Codec Collections Compress Csv JxPath Lang Math Gson JacksonCore JacksonDatabind JacksonXml Chart Time Jsoup Mockito)
#repos=(Csv Cli Lang Chart Gson)
#repos=(Gson)

# -s /scaffoldings
# -d /defects4j_with_dynamtests/corpus_only_public
# -o /defects4j_with_dynamtests/corpus_only_public/csv
# -t /tmp/checkouts


# Check arguments
while getopts ":s:d:o:t:" opt; do
    case $opt in
        s) scaffoldings_dir="$OPTARG"
            ;;
        d) d4j_data="$OPTARG"
            ;;
        o) output_dataset_d4j="$OPTARG"
            ;;
        t) dir_checkouts="$OPTARG"
            ;;
        \?)
            echo "Unknown option: -$OPTARG" >&2
            usage
            ;;
        :)
            echo "No argument provided: -$OPTARG." >&2
            usage
            ;;
  esac
done


# perl build_dataset_d4j.pl -p Gson -s /scaffoldings -d /defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version -o /defects4j_with_dynamtests/corpus_only_public/csv -t /tmp/checkouts

# -p Gson 
# -s /scaffoldings
# -d /defects4j_with_dynamtests/corpus_only_public
# -o /defects4j_with_dynamtests/corpus_only_public/csv
# -t /tmp/checkouts
start_time=$(date +%s)

for repo in ${repos[@]}; do
    echo ""
    echo "Construyendo dataset_d4j for project: ${repo}..."
    # echo ""
    #file_generated_tests="$generated_tests_dir/$repo"
    # scaffoldings_dir_project="$scaffoldings_dir/${repo}"
    # file_generated_tests_project="$generated_tests_dir/${repo}_generated_tests.csv"
    # output_dir_project="$generated_tests_dir/${repo}"
    # echo "scaffoldings_dir_project: ${scaffoldings_dir_project}"
    # echo "file_generated_tests_project: ${file_generated_tests_project}"
    # echo "output_dir_project: ${output_dir_project}"
    echo ""
    if [ -n "$scaffoldings_dir" ]; then
        perl build_csv_corpus_d4j.pl -p "$repo" -s "$scaffoldings_dir" -d "$d4j_data" -o "$output_dataset_d4j" -t "$dir_checkouts"
    else
        perl build_csv_corpus_d4j.pl -p "$repo" -d "$d4j_data" -o "$output_dataset_d4j" -t "$dir_checkouts"
    fi
    echo ""
    echo "Finish generated_tests in scaffoldings for project: ${repo}..."
    echo ""
    echo ""
done

end_time=$(date +%s)
elapsed_seconds=$((end_time - start_time))
elapsed_time=$(printf '%02d:%02d:%02d\n' $((elapsed_seconds / 3600)) $(( (elapsed_seconds % 3600) / 60 )) $((elapsed_seconds % 60)))
echo "Tiempo total de ejecución: ${elapsed_time}"
echo ""
echo ""


