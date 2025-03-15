import os
import argparse
import json
import shutil
import time
from tqdm import tqdm


DEFECTS4J_PROJECTS_BY_REPO_ID = {
    18845024: "Closure -> https://github.com/google/closure-compiler",
    212343: "Cli -> https://github.com/apache/commons-cli",
    206371: "Codec -> https://github.com/apache/commons-codec",
    206362: "Collections -> https://github.com/apache/commons-collections",
    2580769: "Compress -> https://github.com/apache/commons-compress",
    10637893: "Csv -> https://github.com/apache/commons-csv",
    11304840: "JxPath -> https://github.com/apache/commons-jxpath",
    206378: "Lang -> https://github.com/apache/commons-lang/",
    24928494: "Math -> https://github.com/apache/commons-math",
    32538871: "Gson -> https://github.com/google/gson",
    3037907: "JacksonCore -> https://github.com/FasterXML/jackson-core",
    3038937: "JacksonDatabind -> https://github.com/FasterXML/jackson-databind",
    1210290: "JacksonXml -> https://github.com/FasterXML/jackson-dataformat-xml",
    50873393: "Chart -> https://github.com/jfree/jfreechart",
    1756350: "Time -> https://github.com/JodaOrg/joda-time",
    442430: "JSoup -> https://github.com/jhy/jsoup",
    6207167: "Mockito -> https://github.com/mockito/mockito"
}

def get_total_repos(path: str):
    list_repos_ids = []
    count_repos = 0

    # Recorre los elementos en el directorio actual
    #for elemento in os.listdir('.'):
    for elemento in os.listdir(path):
        path_elemento = os.path.join(path, elemento)
        # Verifica si el elemento es una carpeta
        if os.path.isdir(path_elemento):
            #print("elemento es folder: " + elemento)
            list_repos_ids.append(int(elemento))
            count_repos += 1
        
        #if count_repos >= 5:
        #    break
    
    return count_repos, list_repos_ids


path = "E:/000_Tesis/DynaMTests/mining_results/train/output"
count, list_repos = get_total_repos(path)
#print(list_repos)

for repo_id in list_repos:
    if repo_id in DEFECTS4J_PROJECTS_BY_REPO_ID:
        print(f"Si existe el repo: {repo_id}")

#if 17563501 in DEFECTS4J_PROJECTS_BY_REPO_ID:
#    print("Si existe")