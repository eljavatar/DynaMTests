#!/usr/bin/env bash

repos=(Closure Cli Codec Collections Compress Csv JxPath Lang Math Gson JacksonCore JacksonDatabind JacksonXml Chart Time Jsoup Mockito)
#repos=(Csv Cli Lang Chart Gson)
#repos=(Gson)

repo_type=f

start_time=$(date +%s)

export_focal_classes() {
	json_array=[]
	for repo in ${repos[@]}; do
		results=`defects4j query -p ${repo} -q "classes.modified"` # This prints list (of records) of classes modified (fixed) by bug.id by each repo and save in @results
		results=($(echo "$results" | sed 's/\"//g'))
		for res in ${results[@]}; do
			bugid=$(echo $res | cut -d "," -f 1)
			focal_classes=$(echo $res | cut -d "," -f 2)
			# IFS=';' read -ra focal_classes <<< "$focal_classes"
			focal_classes=$(echo $focal_classes | jq -R -s -c 'split(";")')
			revision=${repo}_${bugid}_${repo_type}
			echo "project: $revision class: ${focal_classes[@]}"
			json_array=$(echo "$json_array" | jq --arg project "${revision}" --argjson classes "$focal_classes" '. += [{"project": $project, "classes": $classes}]')
		done
	done
	echo $json_array > focal_classes.json
}

export_focal_classes

end_time=$(date +%s)
elapsed_seconds=$((end_time - start_time))
elapsed_time=$(printf '%02d:%02d:%02d\n' $((elapsed_seconds / 3600)) $(( (elapsed_seconds % 3600) / 60 )) $((elapsed_seconds % 60)))
echo "Tiempo total de ejecución: ${elapsed_time}"
echo ""