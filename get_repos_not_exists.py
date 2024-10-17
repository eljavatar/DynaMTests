import os


def list_carpetas(path: str):
    # Lista para almacenar los nombres de las carpetas
    carpetas = set()

    # Recorre los elementos en el directorio actual
    #for elemento in os.listdir('.'):
    for elemento in os.listdir(path):
        ruta_elemento = os.path.join(path, elemento)
        # Verifica si el elemento es una carpeta
        if os.path.isdir(ruta_elemento):
            #print("elemento es folder: " + elemento)
            carpetas.add(elemento)

    # Ordena la lista de carpetas
    #carpetas.sort()
    return carpetas


outs_not_exists = list_carpetas("/root/mining_results/train/output_empty/1_repo_not_exists")

carpetas = set()
#carpetas.update(fromtest3)
carpetas.update(outs_not_exists)
#print(f"carpetas = {len(carpetas)}")


carpetas = sorted(list(carpetas))
# Escribe los nombres de las carpetas en un archivo
with open('/root/repos_not_exists.txt', 'w') as archivo:
    for carpeta in carpetas:
        archivo.write(carpeta + '\n')

print('La lista de carpetas ha sido guardada en "repos_not_exsits.txt" con ' + str(len(carpetas)) + ' items.')
