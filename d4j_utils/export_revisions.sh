#!/usr/bin/env bash

repos=(Closure Cli Codec Collections Compress Csv JxPath Lang Math Gson JacksonCore JacksonDatabind JacksonXml Chart Time Jsoup Mockito)
#repos=(Csv Cli Lang Chart Gson)
#repos=(Gson)
# repos=(Jsoup)


#revisions_dir=E:/000_Tesis/defects4j/framework/custom/defects4j_revisions
revisions_dir=/defects4j_revisions
repo_type=f

start_time=$(date +%s)

export_revisions() {
	for repo in ${repos[@]}; do
		cd $revisions_dir
		results=(`defects4j query -p ${repo} -q "bug.id"`) # This prints list (of numbers) of bug versions by each repo and save in @results
		for id in ${results[@]}; do
			repo_name=${repo}_${id}_${repo_type}
			repo_path=${revisions_dir}/${repo_name}
			( defects4j checkout -p $repo -v ${id}${repo_type} -w ${revisions_dir}/${repo_name} ) || continue
			cd $repo_name && defects4j compile # This not find directory
			# cd $revisions_dir/$repo_name && defects4j compile # This not find directory
		done
	done
}


export_revisions

end_time=$(date +%s)
elapsed_seconds=$((end_time - start_time))
elapsed_time=$(printf '%02d:%02d:%02d\n' $((elapsed_seconds / 3600)) $(( (elapsed_seconds % 3600) / 60 )) $((elapsed_seconds % 60)))
echo "Tiempo total de ejecución: ${elapsed_time}"
echo ""