# Pipeline de construcción del corpus DynaMTests — pasos de ejecución por script

**Propósito del documento.** Consolidar en un único artefacto, verificado contra el código, la secuencia completa de pasos que ejecuta cada script del proyecto DynaMTests: desde la minería AST sobre repositorios públicos hasta la obtención de los CSV de entrenamiento, y desde la exportación de revisiones Defects4J hasta el CSV de evaluación. Se incluyen las recetas exactas de ensamblado de las tres representaciones de entrada (`src_fm_fc_ms_ff`, `src_fm_fc_dctx` y `src_fm_fc_dctx_priv`), el contrato de datos entre etapas y los riesgos detectados.

**Alcance.** Se documentan los cuatro scripts del flujo principal (secciones 1 a 4), los cuatro módulos de soporte del análisis AST (sección 5), la secuencia de construcción del corpus de evaluación Defects4J, incluidos sus envoltorios de shell y Perl (sección 6), y los seis utilitarios de ejecución manual (sección 7). Cada paso termina con una referencia `file:line` que lo ancla al código fuente.

**Nota sobre fixtures.** Los archivos [`MyClass.java`](MyClass.java:1), la carpeta `000_java_classes_prueba/` y el JSON [`repos_prueba.json`](repos_prueba.json:1) son fixtures de prueba usados por la batería de tests del propio repositorio. No son insumos del pipeline y no participan en ninguna de las etapas descritas; `MyClass.java` y `000_java_classes_prueba/` se referencian únicamente desde el arnés de depuración [`test_extract_dependencies()`](find_map_tests_cases_from_repo.py:407), cuya invocación está comentada.

**Convención de etiquetas.** Las etiquetas conceptuales `FM_FC_MS_FF` y `FM_FC_DCTX` **no existen como literales** en el código: corresponden a las variables `src_fm_fc_ms_ff` y `src_fm_fc_dctx`, más la variante adicional `src_fm_fc_dctx_priv`, todas emitidas por [`build_format_corpus()`](build_corpus.py:416).

---

## 1) Script find_map_tests_cases_from_repo.py : descarga los repositorios con clonado superficial, extrae la metadata del AST y empareja cada caso de prueba con un método focal, exportando un JSON por caso mapeado.

### 1.1 Configuración de módulo y dependencias

1.1.1 Se importan las dependencias del sistema (`argparse`, `subprocess`, `glob`, `shutil`, `multiprocessing.Pool`, `tqdm`, `GitPython`, `command_runner`) ([`find_map_tests_cases_from_repo.py:1-25`](find_map_tests_cases_from_repo.py:1)).

1.1.2 Se importan las tres piezas del analizador: [`ClassParser`](find_map_tests_cases_from_repo.py:18), [`DependencyClassParser`](find_map_tests_cases_from_repo.py:19) y [`DependencyParserUtils`](find_map_tests_cases_from_repo.py:21).

1.1.3 Se resuelve la ruta absoluta del script en [`PATH_SCRIPT`](find_map_tests_cases_from_repo.py:27) y su directorio en [`DIR_SCRIPT`](find_map_tests_cases_from_repo.py:28); este último se usa para restaurar el directorio de trabajo al final del análisis.

1.1.4 Se leen las credenciales de GitHub por índice directo de `os.environ` en [`GITHUB_USER`](find_map_tests_cases_from_repo.py:32) y [`GITHUB_TOKEN`](find_map_tests_cases_from_repo.py:33); la ausencia de cualquiera de las dos aborta la importación del módulo con `KeyError` antes de validar argumentos.

### 1.2 Ejecución del flujo por repositorio

Se documenta primero la unidad de trabajo por repositorio ([`analyze_project()`](find_map_tests_cases_from_repo.py:99) y su subrutina de minería) y después la orquestación del lote.

#### 1.2.1 Ejecución del método `parse_args()`

1.2.1.1 Se construye un `ArgumentParser` y se definen seis parámetros en [`parse_args()`](find_map_tests_cases_from_repo.py:798).

1.2.1.2 Se define `--repos_file`, sin valor por defecto, con la ruta del JSON que contiene la lista de repositorios a procesar en lote ([`find_map_tests_cases_from_repo.py:803-809`](find_map_tests_cases_from_repo.py:803)).

1.2.1.3 Se define `--repo_url` con la URL de un único repositorio y valor por defecto `https://github.com/google/gson` ([`find_map_tests_cases_from_repo.py:810-817`](find_map_tests_cases_from_repo.py:810)).

1.2.1.4 Se define `--repo_id` con el identificador textual del repositorio y valor por defecto `32538871` ([`find_map_tests_cases_from_repo.py:818-825`](find_map_tests_cases_from_repo.py:818)).

1.2.1.5 Se definen `--tmp`, `--output` y `--output_empty` como las carpetas de clonado temporal, de salida del dataset y de clasificación de fallos ([`find_map_tests_cases_from_repo.py:826-846`](find_map_tests_cases_from_repo.py:826)). El valor literal por defecto de estos tres parámetros no se transcribe en la sección de referencia (a confirmar).

1.2.1.6 Se retorna `vars(parser.parse_args())` como diccionario ([`find_map_tests_cases_from_repo.py:848`](find_map_tests_cases_from_repo.py:848)).

#### 1.2.2 Ejecución del método `analyze_project()`

##### 1.2.2.1 Preparación del clon, de las rutas y de las credenciales

1.2.2.1.1 Se extraen `url` y `repo_id` del diccionario del repositorio ([`analyze_project()`](find_map_tests_cases_from_repo.py:99), líneas [104-105](find_map_tests_cases_from_repo.py:104)).

1.2.2.1.2 Se realiza una copia profunda del diccionario con `copy.deepcopy` y se elimina la clave `num_instances` si existe ([`find_map_tests_cases_from_repo.py:107-111`](find_map_tests_cases_from_repo.py:107)).

1.2.2.1.3 Se crean la carpeta temporal, el directorio destino del repositorio y las rutas `repo_path` y `dataset_out` ([`find_map_tests_cases_from_repo.py:114-118`](find_map_tests_cases_from_repo.py:114)).

1.2.2.1.4 Se inyectan usuario y token en la URL sustituyendo `https://` por `https://{GITHUB_USER}:{GITHUB_TOKEN}@` ([`find_map_tests_cases_from_repo.py:120-121`](find_map_tests_cases_from_repo.py:120)).

1.2.2.1.5 Se clona el repositorio invocando [`clone_repo()`](find_map_tests_cases_from_repo.py:82) dentro de un `try`; ante excepción se marca `error_cloning = True` ([`find_map_tests_cases_from_repo.py:126-130`](find_map_tests_cases_from_repo.py:126)).

1.2.2.1.6 En caso de error de clonado se fuerza el borrado de la carpeta con `shutil.rmtree(..., ignore_errors=True)`, se espera 3 segundos y, si el directorio persiste vacío, se intenta `os.rmdir` ([`find_map_tests_cases_from_repo.py:134-142`](find_map_tests_cases_from_repo.py:134)).

1.2.2.1.7 Se fija `language = 'java'` y se invoca [`find_map_test_cases()`](find_map_tests_cases_from_repo.py:192) con `repo_path`, el lenguaje, `dataset_out`, el diccionario del repositorio y la bandera `error_cloning` ([`find_map_tests_cases_from_repo.py:146-148`](find_map_tests_cases_from_repo.py:146)).

1.2.2.1.8 Se desempaqueta la tupla de siete elementos retornada en `tot_tclass, tot_tc, tot_tclass_fclass, tot_mtc, repo_exists, repo_has_test_files, error_finding_java_files`; tras el desempaquetado, `tot_mtc` pasa a ser el entero de casos mapeados ([`find_map_tests_cases_from_repo.py:149`](find_map_tests_cases_from_repo.py:149)).

##### 1.2.2.2 Ejecución del método `find_map_test_cases()`

1.2.2.2.1 Se abre el archivo `log.txt` en el directorio de salida, se escribe la cabecera con `repo_id` y `url`, se inicializan las banderas `repo_exists = True`, `repo_has_test_files = True` y `error_finding_java_files = False`, y se evalúa la disponibilidad del clon: si no hubo error de clonado y la ruta existe se cambia el directorio de trabajo al clon y, en caso contrario, se registra `Path repo not exists`, se cierra el log y se retorna `0, 0, 0, 0, repo_exists, True, True`, con las dos últimas banderas forzadas para que la clasificación dependa solo de `repo_exists` ([`find_map_test_cases()`](find_map_tests_cases_from_repo.py:192), líneas [199-216](find_map_tests_cases_from_repo.py:199)).

1.2.2.2.2 Se ejecuta `grep -l -r @Test --include \*.java` mediante `subprocess.check_output(..., shell=True)` y se decodifica la salida en ASCII para obtener `test_files` ([`find_map_tests_cases_from_repo.py:219-222`](find_map_tests_cases_from_repo.py:219)), con tres desenlaces posibles:
   - Retorno con archivos: se continúa con el inventario de archivos Java ([`find_map_tests_cases_from_repo.py:256`](find_map_tests_cases_from_repo.py:256)).
   - Código de salida 1: se interpreta como ausencia de tests, se marca `repo_has_test_files = False` y se retorna la tupla con ceros ([`find_map_tests_cases_from_repo.py:223-228`](find_map_tests_cases_from_repo.py:223), retorno en [237](find_map_tests_cases_from_repo.py:237)).
   - Otro `CalledProcessError` o excepción no controlada: se registra con traza completa, se marca `error_finding_java_files = True` y se retorna ([`find_map_tests_cases_from_repo.py:229-245`](find_map_tests_cases_from_repo.py:229)).

1.2.2.2.3 Se construye el inventario de archivos Java con `glob.glob('**/*.java', recursive=True)`, normalizando las barras a `/` para Windows y eliminando el prefijo `./`; ante cualquier excepción se registra la traza, se marca `error_finding_java_files = True` y se retorna ([`find_map_tests_cases_from_repo.py:256-267`](find_map_tests_cases_from_repo.py:256)), y a partir de ese inventario:
   - Se calcula el conjunto de clases focales candidatas por diferencia de conjuntos entre todos los `.java` y los archivos de test, descartando toda ruta que contenga `src/test`, y se genera la versión normalizada en minúsculas en `focal_files_norm` ([`find_map_tests_cases_from_repo.py:274-276`](find_map_tests_cases_from_repo.py:274)).
   - Se escriben en el log los totales de archivos Java, clases de prueba y clases focales candidatas ([`find_map_tests_cases_from_repo.py:278-281`](find_map_tests_cases_from_repo.py:278)).

1.2.2.2.4 Se empareja Clase de Prueba → Clase Focal por nombre, normalizando la ruta de cada archivo de prueba con el reemplazo de `/src/test/` por `/src/main/` ([`find_map_tests_cases_from_repo.py:289`](find_map_tests_cases_from_repo.py:289)):
   - Se extrae el nombre de clase y se elimina el sufijo o el prefijo `test` en minúsculas, recalculando el nombre del archivo ([`find_map_tests_cases_from_repo.py:291-300`](find_map_tests_cases_from_repo.py:291)).
   - Si la ruta normalizada existe en `focal_files_norm` se recupera el índice con `.index()` y se registra el par en `mapped_tests[test_class] = focal_class` ([`find_map_tests_cases_from_repo.py:302-305`](find_map_tests_cases_from_repo.py:302)); `.index()` selecciona la primera coincidencia cuando dos clases focales comparten ruta normalizada.
   - Se calculan `tot_tclass` y `tot_tclass_fclass` y se inicializan `tot_tc` y `tot_mtc` en cero ([`find_map_tests_cases_from_repo.py:313-316`](find_map_tests_cases_from_repo.py:313)).

1.2.2.2.5 Se instancian `ClassParser(language)`, `DependencyClassParser(language)` y `DependencyParserUtils()`, reutilizados para todo el repositorio con el atributo `content` sobrescrito en cada archivo leído, y se abre un segundo archivo `log_error_mapping.txt` con cabecera propia ([`find_map_tests_cases_from_repo.py:322-336`](find_map_tests_cases_from_repo.py:322)).

1.2.2.2.6 Se itera sobre cada par `(test_class, focal_class)` de `mapped_tests` con `tqdm`, registrando el par en el log ([`find_map_tests_cases_from_repo.py:338-341`](find_map_tests_cases_from_repo.py:338)); por cada par se ejecutan de forma secuencial el parseo de casos de prueba (1.2.2.2.6.1), la extracción de métodos focales con su contexto dinámico (1.2.2.2.6.2) y el emparejamiento (1.2.2.2.6.3), con acumulación de totales (1.2.2.2.6.4) y manejo de errores por par (1.2.2.2.6.5).

###### 1.2.2.2.6.1 Ejecución del método `parse_test_cases()`

1.2.2.2.6.1.1 Se invoca [`ClassParser.parse_file()`](ClassParser.py:32) sobre el archivo de prueba ([`find_map_tests_cases_from_repo.py:516`](find_map_tests_cases_from_repo.py:516)).

1.2.2.2.6.1.2 Se recorre cada clase parseada y cada uno de sus métodos, seleccionando únicamente aquellos con `method['is_testcase']` verdadero ([`find_map_tests_cases_from_repo.py:520-522`](find_map_tests_cases_from_repo.py:520)).

1.2.2.2.6.1.3 Se construye la metadata de la clase de prueba copiando el diccionario de la clase, eliminando `methods` y `argument_list`, y se agrega la clave `file` con la ruta del archivo ([`find_map_tests_cases_from_repo.py:525-529`](find_map_tests_cases_from_repo.py:525)).

1.2.2.2.6.1.4 Se anida la clase en `method['class']`, clave consumida posteriormente por la exportación ([`find_map_tests_cases_from_repo.py:530`](find_map_tests_cases_from_repo.py:530)).

1.2.2.2.6.1.5 Se eliminan las claves de minado que no se conservan para los casos de prueba: `use_some_field`, `var_declars`, `class_fields_used`, `class_method_references_used`, `class_methods_used`, `used_external_dependencies`, `methods_from_external_dependencies`, `method_references_from_external_dependencies`, `fields_from_external_dependencies`, `field_dependencies_by_class`, `undefined_method_dependencies` y `class_methods_that_invoke_other_methods` ([`find_map_tests_cases_from_repo.py:532-545`](find_map_tests_cases_from_repo.py:532)).

1.2.2.2.6.1.6 Se conservan deliberadamente `method_dependencies_by_class` y `method_references_dependencies_by_class`, por ser la base de la heurística de invocación única ([`find_map_tests_cases_from_repo.py:541-542`](find_map_tests_cases_from_repo.py:541)).

1.2.2.2.6.1.7 El método queda agregado a la lista de casos de prueba que retorna la función ([`find_map_tests_cases_from_repo.py:547`](find_map_tests_cases_from_repo.py:547)).

###### 1.2.2.2.6.2 Ejecución del método `parse_potential_focal_methods()`

1.2.2.2.6.2.1 Se invoca [`ClassParser.parse_file()`](ClassParser.py:32) sobre el archivo focal ([`find_map_tests_cases_from_repo.py:556`](find_map_tests_cases_from_repo.py:556)).

1.2.2.2.6.2.2 Se enriquece la metadata con el contexto dinámico mediante [`DependencyParserUtils.parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113), pasando el `DependencyClassParser` y la lista completa de archivos focales del repositorio ([`find_map_tests_cases_from_repo.py:558`](find_map_tests_cases_from_repo.py:558)).

1.2.2.2.6.2.3 Se recorren las clases y sus métodos descartando los casos de prueba; el filtro de constructores permanece comentado (`#and not method['constructor']`), de modo que un constructor puede quedar como método focal candidato ([`find_map_tests_cases_from_repo.py:562-565`](find_map_tests_cases_from_repo.py:562)).

1.2.2.2.6.2.4 Se copia el diccionario de la clase, se elimina `argument_list` y se agrega la clave `file`, conservando `fields` y `methods` intactos ([`find_map_tests_cases_from_repo.py:568-573`](find_map_tests_cases_from_repo.py:568)).

1.2.2.2.6.2.5 Se anida la clase focal en `method['class']` y se agrega el método a la lista de candidatos ([`find_map_tests_cases_from_repo.py:574-576`](find_map_tests_cases_from_repo.py:574)).

###### 1.2.2.2.6.3 Ejecución del método `match_test_cases()`

1.2.2.2.6.3.1 Se obtiene el nombre de la clase focal a partir del primer método focal candidato ([`find_map_tests_cases_from_repo.py:591-594`](find_map_tests_cases_from_repo.py:591)).

1.2.2.2.6.3.2 Se construye la lista normalizada de nombres de métodos focales en minúsculas ([`find_map_tests_cases_from_repo.py:598`](find_map_tests_cases_from_repo.py:598)).

1.2.2.2.6.3.3 Por cada caso de prueba se normaliza su nombre a minúsculas y se elimina el sufijo o el prefijo `test` ([`find_map_tests_cases_from_repo.py:601-607`](find_map_tests_cases_from_repo.py:601)).

1.2.2.2.6.3.4 Estrategia 1, coincidencia por nombre: si el nombre normalizado del caso existe en la lista de métodos focales se toma el índice con `.index()` y se recupera el método focal correspondiente ([`find_map_tests_cases_from_repo.py:612-615`](find_map_tests_cases_from_repo.py:612)).

1.2.2.2.6.3.5 En la coincidencia por nombre se eliminan `method_dependencies_by_class` y `method_references_dependencies_by_class` del caso de prueba y se construye `mapped_test_case` con `test_class`, `test_case`, `focal_class` y `focal_method` ([`find_map_tests_cases_from_repo.py:617-626`](find_map_tests_cases_from_repo.py:617)).

1.2.2.2.6.3.6 Se registra la firma del método focal en `tested_focal_methods` usando `focal_method['parameters']` y se escribe el hallazgo en el log ([`find_map_tests_cases_from_repo.py:627-628`](find_map_tests_cases_from_repo.py:627)).

1.2.2.2.6.3.7 Estrategia 2, invocación única: se recopilan las referencias a métodos y las invocaciones cuyo nombre de clase, obtenido con [`DependencyParserUtils.get_class_name()`](dependency_parser_utils.py:308), coincide con el de la clase focal ([`find_map_tests_cases_from_repo.py:632-642`](find_map_tests_cases_from_repo.py:632)).

1.2.2.2.6.3.8 Si hay más de una referencia o más de una invocación asociada a la clase focal, el caso se descarta con `continue` por ambigüedad ([`find_map_tests_cases_from_repo.py:644-646`](find_map_tests_cases_from_repo.py:644)).

1.2.2.2.6.3.9 Se resuelve el método invocado con [`DependencyParserUtils.get_methods_from_external_dependency()`](dependency_parser_utils.py:560) sobre la lista de métodos focales candidatos ([`find_map_tests_cases_from_repo.py:648-650`](find_map_tests_cases_from_repo.py:648)).

1.2.2.2.6.3.10 Si la resolución produce exactamente un método focal se eliminan las dos claves de dependencias, se construye el `mapped_test_case` y se registra la firma en `tested_focal_methods` ([`find_map_tests_cases_from_repo.py:652-666`](find_map_tests_cases_from_repo.py:652)).

1.2.2.2.6.3.11 Se escriben las métricas del emparejamiento (casos de prueba, métodos focales, métodos focales ejercitados, casos mapeados) y se retorna la lista ([`find_map_tests_cases_from_repo.py:671-676`](find_map_tests_cases_from_repo.py:671)).

###### 1.2.2.2.6.4 Acumulación de totales durante el bucle

1.2.2.2.6.4.1 Se acumula `tot_tc` con el número de casos de prueba parseados para el par ([`find_map_tests_cases_from_repo.py:347`](find_map_tests_cases_from_repo.py:347)).

1.2.2.2.6.4.2 Se acumula `tot_mtc` con el número de casos mapeados y se agrega la lista a `mtc_list` cuando el emparejamiento no está vacío ([`find_map_tests_cases_from_repo.py:361-364`](find_map_tests_cases_from_repo.py:361)).

###### 1.2.2.2.6.5 Manejo de errores por par

1.2.2.2.6.5.1 En caso de excepción se marca `has_error_mapping = True`, se imprime tipo y mensaje y se registra la traza completa en `log.txt` y en `log_error_mapping.txt` junto con las rutas de la clase de prueba y de la clase focal, de modo que el bucle continúa con el siguiente par ([`find_map_tests_cases_from_repo.py:365-376`](find_map_tests_cases_from_repo.py:365)).

###### 1.2.2.2.7 Ejecución de los métodos `export_mtc()` y `export()`

1.2.2.2.7.1 Si `mtc_list` no está vacía se invoca [`export_mtc()`](find_map_tests_cases_from_repo.py:679) para exportar los JSON del repositorio ([`find_map_tests_cases_from_repo.py:388-389`](find_map_tests_cases_from_repo.py:388)).

1.2.2.2.7.2 Por cada lista de casos mapeados y por cada caso se realiza una copia profunda ([`find_map_tests_cases_from_repo.py:685-687`](find_map_tests_cases_from_repo.py:685)).

1.2.2.2.7.3 Las claves `test_class` y `focal_class` se extraen de los diccionarios anidados con `pop('class')` ([`find_map_tests_cases_from_repo.py:688-689`](find_map_tests_cases_from_repo.py:688)).

1.2.2.2.7.4 Se agrega el diccionario del repositorio en la clave `repository` ([`find_map_tests_cases_from_repo.py:690`](find_map_tests_cases_from_repo.py:690)).

1.2.2.2.7.5 Se poda cada método de la clase focal eliminando `body`, `class`, `used_private_signatures_of_class`, `used_non_private_signatures_of_class`, `class_private_deps_used`, `class_non_private_deps_used`, `signatures_of_external_dependencies` y `external_dependencies` ([`find_map_tests_cases_from_repo.py:693-701`](find_map_tests_cases_from_repo.py:693)).

1.2.2.2.7.6 El nombre del archivo se compone como `{repo_id}_{mtc_id}.json` dentro del directorio de salida ([`find_map_tests_cases_from_repo.py:707-708`](find_map_tests_cases_from_repo.py:707)).

1.2.2.2.7.7 [`export()`](find_map_tests_cases_from_repo.py:713) elimina el archivo si existe y escribe el JSON serializado con `json.dumps` en UTF-8 ([`find_map_tests_cases_from_repo.py:717-725`](find_map_tests_cases_from_repo.py:717)).

1.2.2.2.7.8 La poda se aplica al método focal y a cada uno de sus métodos, pero no elimina de la clase focal el contexto agregado a nivel de método, de modo que el JSON conserva `class_private_deps_used`, `class_non_private_deps_used` y `external_dependencies` del método focal ([`find_map_tests_cases_from_repo.py:693-701`](find_map_tests_cases_from_repo.py:693)).

1.2.2.2.8 Se escribe el resumen en el log, se cierran ambos archivos, se elimina `log_error_mapping.txt` cuando no hubo errores y se retorna la tupla `(tot_tclass, tot_tc, tot_tclass_fclass, tot_mtc, repo_exists, repo_has_test_files, error_finding_java_files)` ([`find_map_tests_cases_from_repo.py:392-404`](find_map_tests_cases_from_repo.py:392)).

#### 1.2.2.3 Clasificación de fallos por `tot_mtc` en cuatro categorías

1.2.2.3.1 Si `tot_mtc == 0` se listan los archivos del directorio de salida y se copian al subdirectorio de clasificación mediante [`copy_error_files()`](find_map_tests_cases_from_repo.py:92), con orden de precedencia estricto ([`find_map_tests_cases_from_repo.py:152-164`](find_map_tests_cases_from_repo.py:152)).

1.2.2.3.2 Se copia a `1_repo_not_exists/` cuando `not repo_exists` ([`find_map_tests_cases_from_repo.py:155-156`](find_map_tests_cases_from_repo.py:155)).

1.2.2.3.3 Se copia a `2_does_not_have_tests/` cuando `not repo_has_test_files` ([`find_map_tests_cases_from_repo.py:157-158`](find_map_tests_cases_from_repo.py:157)).

1.2.2.3.4 Se copia a `3_error_finding_files/` cuando `error_finding_java_files` ([`find_map_tests_cases_from_repo.py:159-160`](find_map_tests_cases_from_repo.py:159)).

1.2.2.3.5 Se copia a `4_not_matching_tests/` en el caso restante, es decir, repositorio con tests pero sin emparejamientos ([`find_map_tests_cases_from_repo.py:161-162`](find_map_tests_cases_from_repo.py:161)).

1.2.2.3.6 Se elimina el directorio de salida del repositorio con `shutil.rmtree(dataset_out, ignore_errors=True)` ([`find_map_tests_cases_from_repo.py:164`](find_map_tests_cases_from_repo.py:164)).

#### 1.2.2.4 Limpieza del clon temporal y restauración del directorio de trabajo

1.2.2.4.1 Se restaura el directorio del script con `os.chdir(DIR_SCRIPT)` ([`find_map_tests_cases_from_repo.py:167`](find_map_tests_cases_from_repo.py:167)).

1.2.2.4.2 Se intenta `git.rmtree(repo_path)` y, ante excepción, se recurre a `shutil.rmtree(..., ignore_errors=True)` imprimiendo el error ([`find_map_tests_cases_from_repo.py:169-177`](find_map_tests_cases_from_repo.py:169)).

#### 1.2.2.5 Reporte de estadísticas del repositorio

1.2.2.5.1 Se imprimen las estadísticas del repositorio (clases de prueba, clases de prueba mapeadas, casos de prueba y casos mapeados) o el mensaje de error de clonado ([`find_map_tests_cases_from_repo.py:181-189`](find_map_tests_cases_from_repo.py:181)).

### 1.3 Ejecución del método `main()`

1.3.1 Se desempaqueta el diccionario de argumentos en variables locales ([`main()`](find_map_tests_cases_from_repo.py:850), líneas [852-857](find_map_tests_cases_from_repo.py:852)).

1.3.2 Si `repos_file` no es `None` se carga el JSON con `json.load` y se invoca [`analyze_repositories()`](find_map_tests_cases_from_repo.py:745) en modo lote ([`find_map_tests_cases_from_repo.py:859-863`](find_map_tests_cases_from_repo.py:859)).

1.3.3 Si `repos_file` es `None` se construye un diccionario con `repo_id` y `url` y se invoca directamente [`analyze_project()`](find_map_tests_cases_from_repo.py:99) para un único repositorio ([`find_map_tests_cases_from_repo.py:864-869`](find_map_tests_cases_from_repo.py:864)).

1.3.4 El bloque de arranque verifica privilegios con `is_admin()`, mientras que la elevación mediante `elevate(main)` permanece comentada ([`find_map_tests_cases_from_repo.py:872-875`](find_map_tests_cases_from_repo.py:872)).

### 1.4 Ejecución del método `analyze_repositories()`

1.4.1 Se registra el instante inicial para el cálculo del tiempo total ([`find_map_tests_cases_from_repo.py:749`](find_map_tests_cases_from_repo.py:749)).

1.4.2 Se determina el número de procesos como `os.cpu_count()`, sin división ni acotamiento ([`find_map_tests_cases_from_repo.py:753`](find_map_tests_cases_from_repo.py:753)).

1.4.3 En el modo reintento se descomenta `folders = get_repos_not_exists()` junto con `random.shuffle(folders)`, y se filtra cada repositorio con `if str(repo['repo_id']) in folders:` antes de agregarlo a `repos` ([`find_map_tests_cases_from_repo.py:760-766`](find_map_tests_cases_from_repo.py:760)).

1.4.4 [`get_repos_not_exists()`](find_map_tests_cases_from_repo.py:733) lee el archivo `/root/repos_not_exists.txt`, elimina los saltos de línea y retorna la lista de identificadores ([`find_map_tests_cases_from_repo.py:736-742`](find_map_tests_cases_from_repo.py:736)); la ruta está fijada a un `HOME` de Linux.

1.4.5 Se crea un `Pool(num_cpus)`, se arma la lista de tuplas `(repo, tmp, output, output_empty)` y se consume con `pool.imap_unordered(analyze_project_wrapper, args_list)`, actualizando la barra `tqdm` por cada repositorio finalizado ([`find_map_tests_cases_from_repo.py:781-787`](find_map_tests_cases_from_repo.py:781)).

1.4.6 Se calcula y se imprime el tiempo transcurrido en segundos y en formato `días, HH:MM:SS` ([`find_map_tests_cases_from_repo.py:790-795`](find_map_tests_cases_from_repo.py:790)).

### 1.5 Ejecución del método `analyze_project_wrapper()`

1.5.1 Se invoca `analyze_project(*args)` y se retorna `1`, valor consumido por la barra de progreso del pool ([`find_map_tests_cases_from_repo.py:728-730`](find_map_tests_cases_from_repo.py:728)).

### 1.6 Reintentos, progreso y clonado

1.6.1 El decorador [`retry()`](find_map_tests_cases_from_repo.py:36) envuelve la función en un bucle `while True`, incrementa `tries` por cada excepción, duerme `wait` segundos mientras `tries <= retries` y, agotados los intentos, re-lanza la última excepción si `reraise` es verdadero ([`find_map_tests_cases_from_repo.py:44-64`](find_map_tests_cases_from_repo.py:44)).

1.6.2 [`clone_repo()`](find_map_tests_cases_from_repo.py:82) está decorado con `@retry(wait=3, retries=3, reraise=True)`, por lo que admite hasta 3 reintentos con 3 segundos de espera ([`find_map_tests_cases_from_repo.py:81`](find_map_tests_cases_from_repo.py:81)).

1.6.3 El clonado se ejecuta con `git.Repo.clone_from` en modo superficial: `depth=1` con las opciones `--shallow-submodules`, `--no-tags` y `--single-branch` ([`find_map_tests_cases_from_repo.py:86`](find_map_tests_cases_from_repo.py:86)).

1.6.4 [`CloneProgress`](find_map_tests_cases_from_repo.py:67) hereda de `RemoteProgress` y sincroniza una barra `tqdm` con `max_count` y `cur_count` en cada actualización ([`find_map_tests_cases_from_repo.py:69-78`](find_map_tests_cases_from_repo.py:69)).

1.6.5 [`copy_error_files()`](find_map_tests_cases_from_repo.py:92) crea el subdirectorio de clasificación con `os.makedirs(..., exist_ok=True)` y copia cada archivo con `shutil.copy` ([`find_map_tests_cases_from_repo.py:93-96`](find_map_tests_cases_from_repo.py:93)).

### 1.7 Arnés de depuración `test_extract_dependencies()`

1.7.1 El método [`test_extract_dependencies()`](find_map_tests_cases_from_repo.py:407) contiene una ruta local fija a `000_java_classes_prueba`, una lista manual de archivos Java y la invocación de `parse_potential_focal_methods` sobre `FocalContext.java` ([`find_map_tests_cases_from_repo.py:417-449`](find_map_tests_cases_from_repo.py:417)).

1.7.2 Su única invocación está comentada, por lo que no participa del flujo productivo ni consume fixtures del pipeline ([`find_map_tests_cases_from_repo.py:328`](find_map_tests_cases_from_repo.py:328)).

---

## 2) Script clean_duplicates_and_build_dataset.py : recorre los JSON de minería, agrupa los pares `test_case`-`focal_method` en un conjunto global de deduplicación, excluye los repositorios de Defects4J y copia los JSON supervivientes a `dataset/{split}/{repo_id}/`.

### 2.1 Configuración de módulo y dependencias

2.1.1 Se importan `os`, `argparse`, `json`, `shutil`, `time` y `tqdm` ([`clean_duplicates_and_build_dataset.py:1-6`](clean_duplicates_and_build_dataset.py:1)).

2.1.2 Se declara `DEFECTS4J_PROJECTS_BY_REPO_ID`, un diccionario de 17 entradas que mapea `repo_id` a `Nombre -> URL`; la constante no se consulta en ninguna función del script ([`clean_duplicates_and_build_dataset.py:9-27`](clean_duplicates_and_build_dataset.py:9)).

2.1.3 Se declara `DEFECTS4J_PROJECTS_URLS`, un `set` con las 17 URLs de los proyectos Defects4J, que es la única estructura de Defects4J que participa del filtrado ([`clean_duplicates_and_build_dataset.py:29-47`](clean_duplicates_and_build_dataset.py:29)).

2.1.4 La URL de `Lang` se registra con barra final, de modo que la comparación por igualdad exige que el JSON de repositorios use exactamente ese literal ([`clean_duplicates_and_build_dataset.py:29-47`](clean_duplicates_and_build_dataset.py:29)).

### 2.2 Ejecución del método `parse_args()`

2.2.1 Se construye un `ArgumentParser` con dos parámetros ([`parse_args()`](clean_duplicates_and_build_dataset.py:172), líneas [176-190](clean_duplicates_and_build_dataset.py:176)).

2.2.2 `--mining_input` define la raíz de los resultados de minería, con valor por defecto `E:/000_Tesis/project_tesis_build_dataset/mining_results` ([`clean_duplicates_and_build_dataset.py:177-183`](clean_duplicates_and_build_dataset.py:177)).

2.2.3 `--output_dataset` define la raíz del dataset de salida, con valor por defecto `E:/000_Tesis/project_tesis_build_dataset/dataset` ([`clean_duplicates_and_build_dataset.py:184-189`](clean_duplicates_and_build_dataset.py:184)).

2.2.4 Se retorna `vars(parser.parse_args())` como diccionario; no existe parámetro de semilla, de proporciones de partición ni de encoding ([`clean_duplicates_and_build_dataset.py:191`](clean_duplicates_and_build_dataset.py:191)).

### 2.3 Ejecución del método `main()`

2.3.1 Se desempaquetan `mining_input` y `output_dataset` del diccionario de argumentos ([`main()`](clean_duplicates_and_build_dataset.py:194), líneas [196-197](clean_duplicates_and_build_dataset.py:196)).

2.3.2 Se registra el instante inicial y se delega todo el trabajo a [`clean_duplicates()`](clean_duplicates_and_build_dataset.py:142) ([`clean_duplicates_and_build_dataset.py:199-200`](clean_duplicates_and_build_dataset.py:199)).

2.3.3 Se imprime el tiempo total en segundos y en formato `HH:MM:SS`, sin generar archivo de log ni de estadísticas ([`clean_duplicates_and_build_dataset.py:203-207`](clean_duplicates_and_build_dataset.py:203)).

2.3.4 El bloque `__main__` invoca `main()` sin envoltorio adicional ([`clean_duplicates_and_build_dataset.py:210-211`](clean_duplicates_and_build_dataset.py:210)).

### 2.4 Ejecución del método `clean_duplicates()`

2.4.1 Se fijan las tres rutas de entrada concatenando la raíz con `train/output`, `validation/output` y `test/output` ([`clean_duplicates()`](clean_duplicates_and_build_dataset.py:142), líneas [143-145](clean_duplicates_and_build_dataset.py:143)).

2.4.2 Se fijan las tres rutas de salida como `dataset/train`, `dataset/validation` y `dataset/test` ([`clean_duplicates_and_build_dataset.py:147-149`](clean_duplicates_and_build_dataset.py:147)).

2.4.3 Las tres carpetas de salida se crean de forma incondicional antes de verificar la existencia de las entradas, por lo que pueden quedar splits vacíos ([`clean_duplicates_and_build_dataset.py:151-153`](clean_duplicates_and_build_dataset.py:151)).

2.4.4 Se inicializan los conjuntos globales compartidos `unique_all_tests` (pares método focal + caso de prueba) y `unique_all_focal_methods` (cuerpos focales) ([`clean_duplicates_and_build_dataset.py:155-156`](clean_duplicates_and_build_dataset.py:155)).

2.4.5 La deduplicación se ejecuta en el orden train, validation y test, de modo que la precedencia efectiva es train > validation > test ([`clean_duplicates_and_build_dataset.py:158-162`](clean_duplicates_and_build_dataset.py:158)).

2.4.6 Se imprimen los totales de tests únicos, métodos focales únicos y aceptados/ignorados por split ([`clean_duplicates_and_build_dataset.py:165-169`](clean_duplicates_and_build_dataset.py:165)).

### 2.5 Ejecución del método `extract_uniques()`

2.5.1 Si la ruta de entrada no existe se imprime `Not exists path` y se retorna `0, 0` sin error ([`extract_uniques()`](clean_duplicates_and_build_dataset.py:68), líneas [69-71](clean_duplicates_and_build_dataset.py:69)).

2.5.2 Se cuenta el número de repositorios mediante [`get_total_repos()`](clean_duplicates_and_build_dataset.py:50), que cuenta los subdirectorios del primer nivel ([`clean_duplicates_and_build_dataset.py:73-74`](clean_duplicates_and_build_dataset.py:73)).

2.5.3 Se inicializan los contadores `accepted_tests` e `ignored_tests` ([`clean_duplicates_and_build_dataset.py:76-77`](clean_duplicates_and_build_dataset.py:76)).

2.5.4 Se itera sobre los subdirectorios del primer nivel de la entrada con `next(os.walk(path_in))[1]`, donde cada subdirectorio corresponde a un `repo_id` ([`clean_duplicates_and_build_dataset.py:80-82`](clean_duplicates_and_build_dataset.py:80)).

2.5.5 Se itera sobre los archivos de cada carpeta de repositorio con `tqdm` y se seleccionan únicamente los que terminan en `.json` ([`clean_duplicates_and_build_dataset.py:85-88`](clean_duplicates_and_build_dataset.py:85)).

2.5.6 Cada archivo se carga completo con `json.load` y se extraen exactamente tres campos: `data['test_case']['body']`, `data['focal_method']['body']` y `data['repository']` ([`clean_duplicates_and_build_dataset.py:90-97`](clean_duplicates_and_build_dataset.py:90)).

2.5.7 Filtro Defects4J: si `repository['url']` pertenece a `DEFECTS4J_PROJECTS_URLS` el registro se cuenta como ignorado y se descarta antes de cualquier deduplicación ([`clean_duplicates_and_build_dataset.py:99-101`](clean_duplicates_and_build_dataset.py:99)).

2.5.8 Se construye la clave de deduplicación `pair_test_and_focal = method_src_code + test_src_code`, es decir, una concatenación directa de `focal_method['body']` y de `test_case['body']` sin delimitador ([`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103)).

2.5.9 La clave incluye la firma de ambos métodos y conserva saltos de línea, tabulaciones y espacios originales, porque `body` es la declaración completa del nodo de método y en esta etapa no se aplica normalización textual ([`ClassParser.py:489`](ClassParser.py:489)).

2.5.10 Los bloques de deduplicación por dimensiones separadas (`test_src_code in unique_all_tests` y `method_src_code in unique_all_focal_methods`) permanecen comentados, de modo que un mismo caso de prueba puede repetirse si se empareja con métodos focales distintos ([`clean_duplicates_and_build_dataset.py:105-113`](clean_duplicates_and_build_dataset.py:105), [121-126](clean_duplicates_and_build_dataset.py:121)).

2.5.11 Se descarta el registro si `test_src_code` es `None`, si `method_src_code` es `None` o si el par ya figura en `unique_all_tests` ([`clean_duplicates_and_build_dataset.py:115-119`](clean_duplicates_and_build_dataset.py:115)).

2.5.12 Se acepta el registro creando la carpeta de destino del repositorio, añadiendo el par a `unique_all_tests`, añadiendo el cuerpo focal a `unique_all_focal_methods` y copiando el archivo con `shutil.copy` conservando el nombre original ([`clean_duplicates_and_build_dataset.py:128-133`](clean_duplicates_and_build_dataset.py:128)).

2.5.13 `unique_all_focal_methods` se puebla pero nunca se consulta como criterio de rechazo; solo se usa para imprimir el total de métodos focales únicos ([`clean_duplicates_and_build_dataset.py:130`](clean_duplicates_and_build_dataset.py:130), [166](clean_duplicates_and_build_dataset.py:166)).

2.5.14 Se retorna la tupla `(accepted_tests, ignored_tests)`, donde `ignored_tests` agrega indistintamente exclusiones Defects4J, cuerpos nulos y duplicados ([`clean_duplicates_and_build_dataset.py:139`](clean_duplicates_and_build_dataset.py:139)).

### 2.6 Naturaleza de la transformación y del archivo de salida

2.6.1 La operación es una copia de bytes con `shutil.copy` del JSON de minería, sin re-serialización, sin poda de claves ni reordenamiento de campos ([`clean_duplicates_and_build_dataset.py:132`](clean_duplicates_and_build_dataset.py:132)).

2.6.2 Se preserva el nombre `{repo_id}_{mtc_id}.json` y el destino es `{output_dataset}/{split}/{repo_id}/{repo_id}_{mtc_id}.json` ([`clean_duplicates_and_build_dataset.py:82`](clean_duplicates_and_build_dataset.py:82), [132](clean_duplicates_and_build_dataset.py:132)).

2.6.3 Ningún registro se reescribe para marcar su origen o su split: la partición se infiere únicamente por la carpeta contenedora ([`clean_duplicates_and_build_dataset.py:128-133`](clean_duplicates_and_build_dataset.py:128)).

2.6.4 El encoding no se especifica al abrir el JSON de minería, por lo que se usa el encoding por defecto del sistema, coherente con la alternativa `cp1252` documentada en la etapa 3 ([`clean_duplicates_and_build_dataset.py:90`](clean_duplicates_and_build_dataset.py:90), [`build_corpus.py:733`](build_corpus.py:733)).

### 2.7 Validaciones, filtros y alcance de la comprobación Defects4J

2.7.1 No existe validación de esquema: solo se accede a `test_case`, `focal_method` y `repository` ([`clean_duplicates_and_build_dataset.py:90-97`](clean_duplicates_and_build_dataset.py:90)).

2.7.2 Los filtros vigentes, en orden de aplicación, son extensión `.json`, `repository['url']` fuera del conjunto Defects4J, `test_case['body']` no nulo, `focal_method['body']` no nulo y par no visto antes en la ejecución ([`clean_duplicates_and_build_dataset.py:87-119`](clean_duplicates_and_build_dataset.py:87)).

2.7.3 No hay umbrales de longitud, de tokens, de métodos por clase ni de tamaño de archivo, y no hay validación sintáctica del código Java: la primera validación con `tree-sitter` ocurre en la etapa 3 ([`clean_duplicates_and_build_dataset.py:87-119`](clean_duplicates_and_build_dataset.py:87)).

2.7.4 La partición train/validation/test no se calcula en este script: se hereda de las tres carpetas de entrada de la partición manual del listado de repositorios ([`clean_duplicates_and_build_dataset.py:143-149`](clean_duplicates_and_build_dataset.py:143)).

2.7.5 La única comprobación relacionada con Defects4J es la exclusión por pertenencia de `repository['url']` al conjunto de 17 URLs; no se cruza el contenido de los métodos focales ni se generan contadores por proyecto ([`clean_duplicates_and_build_dataset.py:99-101`](clean_duplicates_and_build_dataset.py:99)).

2.7.6 Este script no lee las carpetas `1_repo_not_exists`, `2_does_not_have_tests`, `3_error_finding_files` ni `4_not_matching_tests`, por lo que la clasificación de fallos es puramente informativa para el operador ([`find_map_tests_cases_from_repo.py:152-164`](find_map_tests_cases_from_repo.py:152)).

---

## 3) Script build_corpus.py : transforma cada JSON del dataset en una entrada de corpus con la pareja `target` (caso de prueba) y tres representaciones de entrada, y exporta el corpus en JSON por repositorio y en archivos de texto planos por split.

### 3.1 Configuración de módulo y dependencias

3.1.1 Se importan `argparse`, `copy`, `json`, `os`, `re`, `time`, `tqdm` y [`ParserUtils`](ParserUtils.py:13); el módulo `copy` se importa sin uso efectivo ([`build_corpus.py:1-8`](build_corpus.py:1)).

3.1.2 La cabecera de comentarios documenta las dos salidas: `corpus/json/{split}/{repo_id}/{repo_id}_{n}_corpus.json` con las seis claves del registro y `corpus/raw/{split}/` con seis archivos de texto ([`build_corpus.py:11-37`](build_corpus.py:11)).

3.1.3 Se declaran seis listas globales de diagnóstico que se acumulan durante la ejecución y solo se reportan por consola al final, sin escribirse a disco ([`build_corpus.py:40-45`](build_corpus.py:40), [210-225](build_corpus.py:210)).

### 3.2 Ejecución del método `parse_args()`

3.2.1 Se definen doce parámetros ([`parse_args()`](build_corpus.py:716), líneas [720-795](build_corpus.py:720)).

3.2.2 `--input_dataset` apunta a la carpeta de un split del dataset, por defecto `E:/000_Tesis/project_tesis_build_dataset/dataset/train` ([`build_corpus.py:721-728`](build_corpus.py:721)).

3.2.3 `--input_encoding` define el encoding de lectura de los JSON, con valor por defecto `utf-8` y la alternativa `cp1252` documentada para datasets construidos en Windows ([`build_corpus.py:729-735`](build_corpus.py:729)).

3.2.4 `--type_dataset` nombra el split, por defecto `train`, y determina el nombre de las carpetas de salida ([`build_corpus.py:736-741`](build_corpus.py:736)).

3.2.5 `--validate_against_d4j_dataset` activa el cruce con Defects4J, por defecto `True`, y se declara con `type=bool`, de modo que cualquier cadena no vacía —incluido `False`— se convierte en `True` ([`build_corpus.py:742-747`](build_corpus.py:742)).

3.2.6 `--d4j_dataset` define la raíz del dataset Defects4J, por defecto `/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version` ([`build_corpus.py:748-753`](build_corpus.py:748)).

3.2.7 `--output_corpus` define la raíz de salida, por defecto `E:/000_Tesis/project_tesis_build_dataset/corpus/` ([`build_corpus.py:754-759`](build_corpus.py:754)).

3.2.8 Los seis parámetros de delimitadores son `--tag_focal_context_start` (`<FCTX>`), `--tag_focal_context_end` (`</FCTX>`), `--tag_external_context_start` (`<ECTX>`), `--tag_external_context_end` (`</ECTX>`), `--tag_private_focal_context_start` (`<PRIVATE_FCTX>`) y `--tag_private_focal_context_end` (`</PRIVATE_FCTX>`) ([`build_corpus.py:760-795`](build_corpus.py:760)).

### 3.3 Ejecución del método `main()`

3.3.1 Se desempaquetan los doce argumentos en variables locales ([`main()`](build_corpus.py:800), líneas [802-813](build_corpus.py:802)).

3.3.2 Se registra el instante inicial y se instancia `ParserUtils(input_encoding)` ([`build_corpus.py:815-817`](build_corpus.py:815)).

3.3.3 Se construye el índice Defects4J con [`get_focal_methods_by_d4j_project()`](build_corpus.py:680) ([`build_corpus.py:819`](build_corpus.py:819)).

3.3.4 Se invoca [`build_corpus()`](build_corpus.py:80) con todos los parámetros y se imprime el tiempo total ([`build_corpus.py:821-841`](build_corpus.py:821)).

### 3.4 Ejecución de `get_focal_methods_by_d4j_project()`

3.4.1 Si `validate_against_d4j_dataset` es falso se retorna un diccionario vacío ([`get_focal_methods_by_d4j_project()`](build_corpus.py:680), líneas [681-683](build_corpus.py:680)).

3.4.2 Si está activo se recorren los 17 proyectos codificados de forma literal en `list_projects_d4j` ([`build_corpus.py:685-687`](build_corpus.py:685)).

3.4.3 Para cada proyecto se recorre `{d4j_dataset}/{Proyecto}/{version}/methods/{metodo}/metadata.json` ([`build_corpus.py:688-698`](build_corpus.py:688)).

3.4.4 De cada `metadata.json` existente se extrae `focal_method['body']` y se normaliza con [`clean_comments_in_code()`](build_corpus.py:655) más la cadena de reemplazos de puntuación ([`build_corpus.py:700-709`](build_corpus.py:700)).

3.4.5 El cuerpo normalizado se acumula en un `set` por proyecto y el diccionario resultante se indexa por nombre de proyecto ([`build_corpus.py:709-711`](build_corpus.py:709)).

3.4.6 En el lado Defects4J no se aplica [`fix_type_parameters_inconsistences()`](ParserUtils.py:314), mientras que en el lado del dataset sí se aplica, de modo que los cuerpos que requieran esa corrección no coinciden entre ambos lados ([`build_corpus.py:358`](build_corpus.py:358)).

### 3.5 Ejecución del método `build_corpus()`

3.5.1 Se cuentan los repositorios de entrada y se preparan las carpetas `{output_corpus}/json/{type_dataset}` y `{output_corpus}/raw/{type_dataset}` con `os.makedirs` ([`build_corpus()`](build_corpus.py:80), líneas [93-102](build_corpus.py:93)).

3.5.2 Se inicializan las seis listas paralelas que alimentan el corpus plano, junto con el conjunto `unique_sources_targets` ([`build_corpus.py:114-122`](build_corpus.py:114)).

3.5.3 Se itera sobre las carpetas de repositorio con `next(os.walk(input_dataset))[1]` y se crea una carpeta de destino por repositorio, aunque no sobreviva ningún registro ([`build_corpus.py:126-129`](build_corpus.py:126)).

3.5.4 Por cada archivo `.json` se carga el documento con el encoding indicado y se invoca [`extract_data_from_mapped_test_case()`](build_corpus.py:328), que retorna siete valores ([`build_corpus.py:138-149`](build_corpus.py:138)).

3.5.5 Si `target` es `None` el registro se descarta silenciosamente con `continue`; es el punto único de descarte por filtros y errores de sintaxis ([`build_corpus.py:151-152`](build_corpus.py:151)).

3.5.6 Se compara el cuerpo focal normalizado (`src_only_method_body`, segundo elemento de la tupla) contra el `set` de cada proyecto Defects4J y, si coincide, se marca `exists_in_d4j_dataset` y se incrementa el contador del proyecto ([`build_corpus.py:154-161`](build_corpus.py:154)).

3.5.7 Si el método focal existe en el corpus Defects4J el registro se omite del corpus; los conteos por proyecto se imprimen al final ([`build_corpus.py:163-164`](build_corpus.py:163), [204-206](build_corpus.py:204)).

3.5.8 Segunda deduplicación, propia de esta etapa: `source_target = src_only_method_body + target`, y el registro se omite si ya existe en `unique_sources_targets` ([`build_corpus.py:166-170`](build_corpus.py:166)).

3.5.9 El nombre del archivo de corpus se compone como `{nombre_sin_extension}_corpus.json` dentro de la carpeta del repositorio ([`build_corpus.py:174-176`](build_corpus.py:174)).

3.5.10 Se construye el diccionario de seis claves y se exporta con [`export_corpus_json()`](build_corpus.py:263) ([`build_corpus.py:178-187`](build_corpus.py:178)).

3.5.11 Se acumulan en orden los seis valores `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class` e `imports_test_class` en sus listas paralelas ([`build_corpus.py:189-194`](build_corpus.py:189)).

3.5.12 Al final se reportan los conteos de las seis listas de error y el total de errores de sintaxis, se exporta el corpus plano con [`export_corpus_raw()`](build_corpus.py:275) y se imprime el total del split ([`build_corpus.py:210-239`](build_corpus.py:210), [259-260](build_corpus.py:259)).

3.5.13 `get_total_mapped_test_cases()` está implementado pero su invocación y su impresión están comentadas, por lo que es código muerto ([`build_corpus.py:64-77`](build_corpus.py:64), [95-96](build_corpus.py:95)).

### 3.6 Ejecución de `extract_data_from_mapped_test_case()`

3.6.1 Se leen los cuatro bloques `test_class`, `test_case`, `focal_class` y `focal_method`; `repository` está comentado y no se usa ([`extract_data_from_mapped_test_case()`](build_corpus.py:328), líneas [336-339](build_corpus.py:336)).

3.6.2 Filtro estructural 1: se descarta el registro si la firma de la clase focal contiene ` interface ` o empieza con `interface ` ([`build_corpus.py:342-344`](build_corpus.py:342)).

3.6.3 Filtro estructural 2: se descarta si `abstract` aparece en los modificadores del método focal ([`build_corpus.py:346-347`](build_corpus.py:346)).

3.6.4 Filtro estructural 3: se descarta si `@Ignore` aparece en los modificadores del caso de prueba ([`build_corpus.py:349-350`](build_corpus.py:349)).

3.6.5 Se normaliza el `target` eliminando comentarios con [`clean_comments_in_code()`](build_corpus.py:655), aplicando los reemplazos de espaciado en torno a `.`, `(`, `)`, `[`, `]` y `){` y corrigiendo inconsistencias de parámetros de tipo con [`fix_type_parameters_inconsistences()`](ParserUtils.py:314) ([`build_corpus.py:352-354`](build_corpus.py:352)).

3.6.6 Se normaliza el método focal con la misma secuencia, almacenada en `body_method` ([`build_corpus.py:356-358`](build_corpus.py:356)).

3.6.7 Se descarta el registro si [`method_body_is_empty()`](ParserUtils.py:66) resulta verdadero para el `target` o para el cuerpo focal ([`build_corpus.py:360-364`](build_corpus.py:360)).

3.6.8 Se valida sintácticamente el `target` envolviéndolo en `public class AnyClass { ... }` con `validate_all_errors = True`; si hay error se registra en `list_errors_methods_target` y se descarta el registro ([`build_corpus.py:369-377`](build_corpus.py:369)).

3.6.9 Se valida sintácticamente el cuerpo focal con la misma mecánica y la lista `list_errors_methods_source` ([`build_corpus.py:380-388`](build_corpus.py:380)).

3.6.10 Se delega el ensamblado en [`build_format_corpus()`](build_corpus.py:416) y, si la representación estática es `None`, se descarta el registro ([`build_corpus.py:391-405`](build_corpus.py:391)).

3.6.11 Los imports se serializan uniendo la lista de strings con el delimitador `|` y limpiando comentarios y espaciado; un caso de prueba sin imports produce cadena vacía, no `null` ([`build_corpus.py:407-411`](build_corpus.py:407)).

3.6.12 Se retorna la tupla `(target, body_method, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_test_class, imports_focal_class)` ([`build_corpus.py:413`](build_corpus.py:413)).

3.6.13 Todos los filtros descartan el registro completo retornando siete `None`, sin retorno parcial ([`build_corpus.py:328-413`](build_corpus.py:328)).

### 3.7 Ejecución de `build_format_corpus()`: precondiciones y firma de clase

3.7.1 La firma de clase se compone con [`build_class_signature()`](build_corpus.py:631) y se valida de forma tolerante añadiendo `" { }"` con `validate_all_errors = False`; si falla se registra en `list_errors_focal_class_sig` y se retorna `(None, None, None)` ([`build_corpus.py:436-446`](build_corpus.py:436)).

3.7.2 Se recuperan `focal_class['methods']` y `focal_class['fields']` y se fija `key_method_for_extract = 'full_signature'`, con la alternativa `full_signature_parameters` comentada ([`build_corpus.py:448-452`](build_corpus.py:448)).

3.7.3 Se compone la firma de clase en [`build_class_signature()`](build_corpus.py:631) a partir de `class_name`, `superclass`, `interfaces` y `class_signature` ([`build_corpus.py:632-646`](build_corpus.py:632)).

3.7.4 Se limpian comentarios, anotaciones y la llave inicial, y se recompone la firma con la plantilla `'{} {} {} {}'` en el orden modificadores y tipo, nombre, extends, implements; si `class_name` no se encuentra se retorna la firma limpia sin recomponer ([`build_corpus.py:636-646`](build_corpus.py:636)).

### 3.8 Ejecución de `build_format_corpus()`: recetas exactas de las tres representaciones

3.8.1 Componente base de `src_fm_fc_ms_ff`: `class_signature` como primer elemento ([`build_corpus.py:436`](build_corpus.py:436)).

3.8.2 Componente 2 de `src_fm_fc_ms_ff`: `body_method`, declaración del método focal previamente limpiada y normalizada ([`build_corpus.py:356-358`](build_corpus.py:356)).

3.8.3 Componente 3: `full_signature` de cada método con `is_constructor == True`, con `;` añadido, unidos con salto de línea y limpiados ([`build_corpus.py:454-457`](build_corpus.py:454)).

3.8.4 Componente 4: `full_signature` de los métodos no constructores sin modificador `private`, con `;` añadido y limpiados ([`build_corpus.py:459-462`](build_corpus.py:459)).

3.8.5 Componente 5: `original_string` de cada campo sin modificador `private` ([`build_corpus.py:464-466`](build_corpus.py:464)).

3.8.6 Ensamblado de `src_fm_fc_ms_ff` con la plantilla `'{} {{ {} {} {} {} }}'` en el orden **firma de clase, declaración del método focal, constructores, métodos no privados, campos no privados**, es decir, todo el contenido dentro del cuerpo de la clase reconstruida ([`build_corpus.py:469-476`](build_corpus.py:469)).

3.8.7 Normalización de `src_fm_fc_ms_ff`: se colapsan saltos de línea y tabulaciones a un espacio, se colapsan espacios múltiples y se ajustan los espaciados alrededor de `.`, `(`, `)` y corchetes ([`build_corpus.py:477-478`](build_corpus.py:477), con la implementación de [`clean_tabs_and_new_lines()`](build_corpus.py:661)).

3.8.8 Se leen los diccionarios `class_private_deps_used` y `class_non_private_deps_used` producidos por [`parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113) ([`build_corpus.py:481-483`](build_corpus.py:481), [498-500](build_corpus.py:498)).

3.8.9 Firmas privadas usadas: todos los constructores privados de la clase focal, más los métodos privados presentes en `class_private_deps_used['methods']`, más los campos privados de `class_private_deps_used['fields']` mediante `original_string`; se limpian y corrigen con `fix_type_parameters_inconsistences` ([`build_corpus.py:486-492`](build_corpus.py:486)).

3.8.10 Firmas no privadas usadas: todos los constructores no privados, más los métodos no privados no constructores de `class_non_private_deps_used['methods']`, más los campos no privados de `class_non_private_deps_used['fields']`, con la misma limpieza y corrección ([`build_corpus.py:503-509`](build_corpus.py:503)).

3.8.11 Contexto externo: se itera sobre `focal_method['external_dependencies']`, se toma su `class_signature`, se limpian comentarios y anotaciones, se elimina la llave inicial y se corrige el cierre de parámetros de tipo con [`fix_close_type_parameter_sig_class()`](ParserUtils.py:277) ([`build_corpus.py:516-524`](build_corpus.py:516)).

3.8.12 La firma externa se valida de forma tolerante; si falla se registra en `list_errors_external_class_sig` y se aborta la construcción del registro completo ([`build_corpus.py:528-536`](build_corpus.py:528)).

3.8.13 Las firmas internas de la clase externa se componen como la unión de `original_string` de sus campos y `full_signature` de sus métodos, se limpian, se corrigen en parámetros de tipo y se les eliminan las anotaciones de firma ([`build_corpus.py:538-546`](build_corpus.py:538)).

3.8.14 Esas firmas internas se validan de forma tolerante envolviéndolas en una interfaz auxiliar ([`build_corpus.py:548-557`](build_corpus.py:548)).

3.8.15 Cada bloque externo se ensambla con la plantilla `'{} {{ {} }}'`, se normaliza y se envuelve con las etiquetas de contexto externo ([`build_corpus.py:559-563`](build_corpus.py:559)).

3.8.16 Si no hay dependencias externas se emite el par de etiquetas vacío; en caso contrario los bloques se unen con un espacio ([`build_corpus.py:565-568`](build_corpus.py:565)).

3.8.17 Se concatenan todas las firmas focales en el orden firmas no privadas, firmas privadas, campos no privados, constructores y métodos no privados, y el conjunto se valida de forma tolerante envolviéndolo en una interfaz auxiliar; si falla se aborta el registro ([`build_corpus.py:587-596`](build_corpus.py:587)).

3.8.18 `src_fm_fc_dctx` se ensambla con la plantilla `'{}{} {{ {} {} {} }}{} {}'` ([`build_corpus.py:599`](build_corpus.py:599)) y los argumentos en orden estricto: `tag_focal_context_start`, `class_signature`, llave de apertura, `body_method`, `used_non_private_signatures_of_class_str`, `used_private_signatures_of_class_str`, llave de cierre, `tag_focal_context_end` y `src_external_context` ([`build_corpus.py:600-608`](build_corpus.py:600)).

3.8.19 `src_fm_fc_dctx` se normaliza con `clean_tabs_and_new_lines` y con los ajustes de espaciado ([`build_corpus.py:609-610`](build_corpus.py:609)).

3.8.20 `src_fm_fc_dctx_priv` usa la misma plantilla que `src_fm_fc_dctx`, pero el quinto bloque se envuelve adicionalmente con `<PRIVATE_FCTX>...</PRIVATE_FCTX>` ([`build_corpus.py:613-622`](build_corpus.py:613)) y se normaliza con las mismas reglas ([`build_corpus.py:623-624`](build_corpus.py:623)).

3.8.21 Recetas exactas con los delimitadores por defecto de [`build_corpus.py:760-795`](build_corpus.py:760):

- `src_fm_fc_ms_ff` = `«class_signature» { «declaración del método focal» «constructores» «métodos no privados de la clase» «campos no privados de la clase» }`, sin etiquetas ([`build_corpus.py:469-478`](build_corpus.py:469)).
- `src_fm_fc_dctx` = `<FCTX>«class_signature» { «declaración del método focal» «firmas no privadas usadas» «firmas privadas usadas» }</FCTX> «contexto externo»` ([`build_corpus.py:599-610`](build_corpus.py:599)).
- `src_fm_fc_dctx_priv` = `<FCTX>«class_signature» { «declaración del método focal» «firmas no privadas usadas» <PRIVATE_FCTX>«firmas privadas usadas»</PRIVATE_FCTX> }</FCTX> «contexto externo»` ([`build_corpus.py:613-624`](build_corpus.py:613)).
- Bloque externo = `<ECTX>«firma de la clase externa» { «campos usados» «métodos usados con ;» }</ECTX>`, o `<ECTX></ECTX>` cuando no hay dependencias ([`build_corpus.py:559-568`](build_corpus.py:559)).

3.8.22 `«declaración del método focal»` es el valor normalizado de `focal_method['body']` e incluye modificadores, anotaciones, firma, parámetros y bloque de cuerpo ([`build_corpus.py:356-358`](build_corpus.py:356)).

3.8.23 Las tres cadenas pasan por la misma normalización de espacios, de modo que los saltos de línea originales no se preservan en ninguna representación ([`build_corpus.py:477-478`](build_corpus.py:477), [609-610](build_corpus.py:609), [623-624](build_corpus.py:623)).

3.8.24 [`build_format_corpus()`](build_corpus.py:416) retorna la terna `(src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv)`, emitida en una sola pasada con la misma firma de clase, el mismo cuerpo focal y el mismo contexto externo ([`build_corpus.py:627`](build_corpus.py:627)).

### 3.9 Helpers de limpieza y de `ParserUtils` utilizados

3.9.1 [`clean_comments_in_code()`](build_corpus.py:655) compone [`clean_comments()`](ParserUtils.py:101) con [`clean_tabs_and_new_lines()`](build_corpus.py:661) y `strip()` ([`build_corpus.py:656-658`](build_corpus.py:656)).

3.9.2 [`clean_tabs_and_new_lines()`](build_corpus.py:661) sustituye una o más apariciones de `\n` o `\t` por un espacio, colapsa espacios múltiples y aplica `strip()`, sin tratar el retorno de carro aislado ([`build_corpus.py:663-666`](build_corpus.py:663)).

3.9.3 [`clean_class_signature_annotations()`](build_corpus.py:669) y [`clean_methods_signatures_annotations()`](build_corpus.py:674) son envoltorios de [`clean_annotations()`](ParserUtils.py:173) y [`clean_signatures_annotations()`](ParserUtils.py:220) ([`build_corpus.py:670-676`](build_corpus.py:670)).

3.9.4 [`validate_if_code_has_errors()`](ParserUtils.py:30) se invoca en seis puntos: validación estricta del `target` y del cuerpo focal, y validaciones tolerantes de la firma focal, de la firma externa, de las firmas internas externas y del conjunto de firmas focales ([`build_corpus.py:369-388`](build_corpus.py:369), [439](build_corpus.py:439), [529](build_corpus.py:529), [549](build_corpus.py:549), [589](build_corpus.py:589)).

3.9.5 [`fix_type_parameters_inconsistences()`](ParserUtils.py:314) se invoca sobre el `target`, el cuerpo focal, los constructores, los métodos no privados, las firmas privadas usadas, las firmas no privadas usadas y las firmas internas externas ([`build_corpus.py:354`](build_corpus.py:354), [358](build_corpus.py:358), [457](build_corpus.py:457), [462](build_corpus.py:462), [492](build_corpus.py:492), [509](build_corpus.py:509), [545](build_corpus.py:545)).

### 3.10 Rutas, formatos de salida y límites de longitud

3.10.1 Corpus JSON: un archivo por registro en `{output_corpus}/json/{type_dataset}/{repo_id}/{nombre_original}_corpus.json`, escrito con `json.dumps` sin `indent` y con `ensure_ascii` por defecto ([`build_corpus.py:98-99`](build_corpus.py:98), [`export_corpus_json()`](build_corpus.py:263), [267-272](build_corpus.py:267)).

3.10.2 Las seis claves del registro son `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class` e `imports_test_class`, en ese orden de inserción ([`build_corpus.py:178-185`](build_corpus.py:178)).

3.10.3 Corpus plano: seis archivos en `{output_corpus}/raw/{type_dataset}/`, a saber `input_methods_src_fm_fc_ms_ff.txt`, `input_methods_src_fm_fc_dctx.txt`, `input_methods_src_fm_fc_dctx_priv.txt`, `output_tests.txt`, `imports_focal_class.txt` e `imports_test_class.txt` ([`build_corpus.py:284-289`](build_corpus.py:284)).

3.10.4 Los archivos previos se eliminan antes de escribir y se abren simultáneamente en un único bloque `with`; se escribe una línea por registro, en el mismo índice en los seis archivos ([`build_corpus.py:292-325`](build_corpus.py:292)).

3.10.5 No existe truncamiento ni límite de longitud en ninguna representación, ni cota al número de bloques `<ECTX>`, por lo que la longitud de `src_fm_fc_dctx` depende linealmente del número de dependencias externas usadas ([`build_corpus.py:416`](build_corpus.py:416), [519-563](build_corpus.py:519)).

---

## 4) Script convert_json_corpus_to_csv_input.py : recorre el corpus JSON de un split, lo consolida en un `DataFrame` de `pandas`, lo reordena aleatoriamente con semilla fija y lo exporta a un único CSV.

### 4.1 Configuración de módulo y dependencias

4.1.1 Se importan `argparse`, `pandas`, `pathlib.Path`, `tqdm`, `os`, `json` y `time`; el import de `json` corresponde al código alternativo comentado ([`convert_json_corpus_to_csv_input.py:1-6`](convert_json_corpus_to_csv_input.py:1), [61-63](convert_json_corpus_to_csv_input.py:61)).

4.1.2 Se declara `SEED = 42` como constante de módulo, no parametrizable sin editar el archivo ([`convert_json_corpus_to_csv_input.py:8`](convert_json_corpus_to_csv_input.py:8)).

4.1.3 [`get_total_repos()`](convert_json_corpus_to_csv_input.py:10) replica la utilidad de conteo de subdirectorios y se usa solo para alimentar la barra de progreso ([`convert_json_corpus_to_csv_input.py:31-34`](convert_json_corpus_to_csv_input.py:31)).

### 4.2 Ejecución del método `parse_args()`

4.2.1 `--input_json_corpus` apunta a la raíz del corpus JSON, por defecto `E:/000_Tesis/project_tesis_build_dataset/corpus/json` ([`parse_args()`](convert_json_corpus_to_csv_input.py:126), líneas [131-136](convert_json_corpus_to_csv_input.py:131)).

4.2.2 `--input_encoding` tiene valor por defecto `cp1252`, con `utf-8` comentado ([`convert_json_corpus_to_csv_input.py:137-143`](convert_json_corpus_to_csv_input.py:137)).

4.2.3 `--type_corpus` nombra el split y determina tanto la carpeta de entrada como el nombre del CSV, por defecto `validation` ([`convert_json_corpus_to_csv_input.py:144-149`](convert_json_corpus_to_csv_input.py:144)).

4.2.4 `--output_csv_corpus` apunta a la carpeta del corpus CSV, por defecto `E:/000_Tesis/project_tesis_build_dataset/corpus/csv/` ([`convert_json_corpus_to_csv_input.py:150-155`](convert_json_corpus_to_csv_input.py:150)).

4.2.5 Se retorna `vars(parser.parse_args())` ([`convert_json_corpus_to_csv_input.py:157`](convert_json_corpus_to_csv_input.py:157)).

### 4.3 Ejecución del método `main()`

4.3.1 Se desempaquetan `type_corpus`, `input_json_corpus` y `output_csv_corpus`; el encoding se descarta y nunca se propaga a `convert()` ([`main()`](convert_json_corpus_to_csv_input.py:160), líneas [162-164](convert_json_corpus_to_csv_input.py:162)).

4.3.2 La ruta de entrada se compone como `{input_json_corpus}/{type_corpus}`, única relación entre split y directorio ([`convert_json_corpus_to_csv_input.py:166`](convert_json_corpus_to_csv_input.py:166)).

4.3.3 Se delega en [`convert()`](convert_json_corpus_to_csv_input.py:25) y se imprime el tiempo total ([`convert_json_corpus_to_csv_input.py:168-177`](convert_json_corpus_to_csv_input.py:168)).

### 4.4 Ejecución del método `convert()`

4.4.1 Se crea la carpeta de salida con `os.makedirs(..., exist_ok=True)` y se fija la ruta `{output_csv_corpus}/{type_corpus}.csv`, de modo que los archivos resultantes son `train.csv`, `validation.csv` y `test.csv` ([`convert()`](convert_json_corpus_to_csv_input.py:25), líneas [26-27](convert_json_corpus_to_csv_input.py:26)).

4.4.2 Se recorre la carpeta de entrada con `Path(...).iterdir()` y se recogen los `.json` de un solo nivel de subdirectorio, sin recursión ([`convert_json_corpus_to_csv_input.py:36-39`](convert_json_corpus_to_csv_input.py:36)).

4.4.3 Cada archivo se lee con `pd.read_json(file, typ='series', orient='records')` y la serie resultante se acumula en una lista, con la lectura alternativa por `json.load` comentada ([`convert_json_corpus_to_csv_input.py:57-63`](convert_json_corpus_to_csv_input.py:57)).

4.4.4 Se construye el `DataFrame` con `pd.DataFrame(json_data)`, donde cada serie aporta una fila y su índice aporta los nombres de columna ([`convert_json_corpus_to_csv_input.py:72`](convert_json_corpus_to_csv_input.py:72)).

4.4.5 Se reordena aleatoriamente con `df.sample(frac=1, random_state=SEED).reset_index(drop=True)` ([`convert_json_corpus_to_csv_input.py:109-110`](convert_json_corpus_to_csv_input.py:109)).

4.4.6 Se exporta con `df_shuffled.to_csv(out_path, index=False, encoding="utf-8")` ([`convert_json_corpus_to_csv_input.py:113-114`](convert_json_corpus_to_csv_input.py:113)).

4.4.7 Se relee el CSV con `pd.read_csv(out_path)` y se imprime `result.info()` como comprobación de parseabilidad, sin comparar el número de filas con el número de JSON leídos ([`convert_json_corpus_to_csv_input.py:119-122`](convert_json_corpus_to_csv_input.py:119)).

### 4.5 Columnas, orden y escapado

4.5.1 Las columnas son exactamente `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class` e `imports_test_class`, en el orden de inserción de claves del JSON de la etapa 3 ([`build_corpus.py:178-185`](build_corpus.py:178), [`convert_json_corpus_to_csv_input.py:82-88`](convert_json_corpus_to_csv_input.py:82)).

4.5.2 No se aplica selección ni reordenamiento explícito de columnas, ni se renombran columnas, porque los `rename` hacia `source` están comentados ([`convert_json_corpus_to_csv_input.py:105-106`](convert_json_corpus_to_csv_input.py:105)).

4.5.3 No hay columna de identificador, de repositorio, de split ni de índice: el CSV es puramente source-target más los dos campos de imports ([`convert_json_corpus_to_csv_input.py:114`](convert_json_corpus_to_csv_input.py:114)).

4.5.4 El entrecomillado lo resuelve `pandas` con su política por defecto `QUOTE_MINIMAL`, de modo que los campos con comas o comillas se entrecomillan y las comillas internas se duplican ([`convert_json_corpus_to_csv_input.py:113-114`](convert_json_corpus_to_csv_input.py:113)).

4.5.5 El riesgo de desalineación por saltos de línea está mitigado en origen porque [`clean_tabs_and_new_lines()`](build_corpus.py:661) elimina `\n` y `\t` de las tres representaciones y del `target` ([`build_corpus.py:477-478`](build_corpus.py:477), [609](build_corpus.py:609), [623](build_corpus.py:623)).

---

## 5) Scripts de soporte del análisis AST (llamados desde 1, 3 y 4)

### 5.1 Script ClassParser.py : encapsula el parser de `tree-sitter` y traduce un archivo Java en una lista de diccionarios de metadata por clase.

5.1.1 Se consulta la versión instalada de `tree_sitter` con `pkg_resources.get_distribution('tree_sitter').version` ([`ClassParser.__init__()`](ClassParser.py:17), línea [18](ClassParser.py:18)).

5.1.2 Si la versión es menor a `0.22.0` el lenguaje se construye con `Language(tsjava.language(), language)`; en caso contrario, con `Language(tsjava.language())` ([`ClassParser.py:20-23`](ClassParser.py:20)).

5.1.3 Si la versión es menor a `0.22.1` se instancia `Parser()` y se invoca `set_language`; en caso contrario, se usa el constructor `Parser(JAVA_LANGUAGE)` ([`ClassParser.py:25-29`](ClassParser.py:25)).

5.1.4 [`parse_file()`](ClassParser.py:32) abre el archivo y almacena el contenido en `self.content`, retornando lista vacía ante fallo de lectura ([`ClassParser.py:41-46`](ClassParser.py:41)).

5.1.5 Se parsea el contenido en bytes UTF-8 con `self.parser.parse(...)` ([`ClassParser.py:54`](ClassParser.py:54)).

5.1.6 Si `root_node.has_error` es verdadero se retorna `[]`, aplicando la política de mapear únicamente código sintácticamente válido ([`ClassParser.py:57-63`](ClassParser.py:57)).

5.1.7 Se seleccionan los hijos directos del nodo raíz de tipo `package_declaration`, `class_declaration` e `import_declaration`, sin considerar `interface_declaration` ni `enum_declaration` ([`ClassParser.py:65-67`](ClassParser.py:65)).

5.1.8 Se construye `import_list` decodificando el texto de cada nodo de importación y aplicando `lstrip("b'")` ([`ClassParser.py:70-72`](ClassParser.py:70)).

5.1.9 Se derivan `static_imports` mediante [`get_static_imports()`](ClassParser.py:1542) y `class_imports` mediante [`get_class_imports()`](ClassParser.py:1561) ([`ClassParser.py:74-75`](ClassParser.py:74)).

5.1.10 Por cada declaración de clase se obtiene el identificador del primer hijo de tipo `identifier` ([`ClassParser.py:89`](ClassParser.py:89)).

5.1.11 Se obtiene la metadata de clase con [`get_class_metadata()`](ClassParser.py:300) y los campos anotados con Mockito con [`get_fields_using_mockito_annotations()`](ClassParser.py:433) ([`ClassParser.py:90-94`](ClassParser.py:90)).

5.1.12 Se itera sobre `class_body` y por cada hijo `method_declaration` o `constructor_declaration` se marca la existencia de constructor y se obtiene la metadata del método con [`get_function_metadata()`](ClassParser.py:443) ([`ClassParser.py:98-108`](ClassParser.py:98)).

5.1.13 Se resuelven las cadenas de invocación entre métodos de la propia clase mediante [`get_class_methods_that_invoke_other_methods()`](ClassParser.py:128) ([`ClassParser.py:111`](ClassParser.py:111)).

5.1.14 Se completan las claves de clase `methods`, `imports` y `package`, tomando el paquete del texto del nodo `package_declaration`, y se retorna la lista de clases ([`ClassParser.py:113-124`](ClassParser.py:113)).

5.1.15 El diccionario de clase contiene `class_name`, `superclass`, `interfaces`, `class_signature`, `class_modifier`, `has_constructor`, `fields`, `argument_list`, `methods`, `imports` y `package` ([`ClassParser.py:304-316`](ClassParser.py:304)).

5.1.16 El diccionario de campo contiene `original_string`, `modifier`, `field_use_mockito_annotations`, `type`, `declarator` y `var_name` ([`ClassParser.py:377-417`](ClassParser.py:377)).

5.1.17 El diccionario de método declara `method_name`, `parameters`, `parameters_list`, `modifiers`, `type_parameters`, `return`, `body`, `class`, `signature`, `full_signature`, `full_signature_parameters`, `class_method_signature`, `is_testcase`, `test_use_mockito`, `is_constructor`, `is_get_or_set`, `use_some_field`, `class_fields_used`, `class_methods_used`, `class_method_references_used`, `var_declars`, `used_external_dependencies`, `methods_from_external_dependencies`, `method_references_from_external_dependencies`, `fields_from_external_dependencies`, `method_dependencies_by_class`, `method_references_dependencies_by_class`, `field_dependencies_by_class`, `undefined_method_dependencies` y `class_methods_that_invoke_other_methods` ([`ClassParser.py:453-486`](ClassParser.py:453)).

5.1.18 En [`get_function_metadata()`](ClassParser.py:443) se extrae el cuerpo completo con `match_from_span` y se registra el nombre de la clase en `metadata['class']` ([`ClassParser.py:489-490`](ClassParser.py:489)).

5.1.19 Se obtienen nombre, parámetros y clases dependientes con [`get_method_name_and_params()`](ClassParser.py:678), que retorna la lista de parámetros textuales, las clases dependientes y el mapa instancia→clase ([`ClassParser.py:497-498`](ClassParser.py:497)).

5.1.20 Se agregan las dependencias de los campos de la clase con [`get_field_dependencies()`](ClassParser.py:760) y las de instanciaciones y arreglos con [`get_dependencies_from_object_creation()`](ClassParser.py:772) ([`ClassParser.py:501-504`](ClassParser.py:501)).

5.1.21 Se evalúa si el método es getter o setter con [`is_getter_or_setter()`](ClassParser.py:811) y, en caso contrario, se determina el uso de campos con [`use_fields()`](ClassParser.py:879) ([`ClassParser.py:507-514`](ClassParser.py:507)).

5.1.22 Se marca `is_constructor` comparando el tipo de nodo con `constructor_declaration` y `is_testcase` cuando `@Test` aparece en los modificadores ([`ClassParser.py:517-528`](ClassParser.py:517)).

5.1.23 Se construye el mapa de variables locales con [`get_var_declar()`](ClassParser.py:1397) y se incorporan sus tipos a `dependent_classes` ([`ClassParser.py:531-538`](ClassParser.py:531)).

5.1.24 Se resuelven invocaciones con [`get_method_m_deps()`](ClassParser.py:923), referencias de método con [`get_method_m_refs_deps()`](ClassParser.py:1168) y accesos a campos con [`get_method_f_deps()`](ClassParser.py:1278) ([`ClassParser.py:543-550`](ClassParser.py:543)).

5.1.25 Se extraen `modifiers`, `type_parameters` y el tipo de retorno descartando comentarios de línea incrustados ([`ClassParser.py:553-576`](ClassParser.py:553)).

5.1.26 Se componen las cuatro variantes de firma con plantillas `format` diferenciadas; `full_signature` incluye modificadores y parámetros con nombre, y `full_signature_parameters` usa el nombre calificado con los tipos de parámetro ([`ClassParser.py:579-587`](ClassParser.py:579)).

5.1.27 Se separan las dependencias explícitas de las no explícitas según cuatro criterios de descarte: contener `.` sin estar en `dependent_classes`, ser cadena vacía, estar en minúsculas o ser importación estática ([`ClassParser.py:591-612`](ClassParser.py:591)).

5.1.28 Se agregan como explícitas las clases de `field_dependencies_by_class`, `method_references_dependencies_by_class` y `dependent_classes`, excluyendo los tipos de `java.lang` ([`ClassParser.py:614-623`](ClassParser.py:614)).

5.1.29 Se clasifican las invocaciones externas con [`method_is_from_not_explicit_dependencies()`](ClassParser.py:651) y se escriben las listas ordenadas `used_external_dependencies`, `methods_from_external_dependencies` y `undefined_method_dependencies` ([`ClassParser.py:626-638`](ClassParser.py:626)).

5.1.30 [`get_method_m_deps()`](ClassParser.py:923) recopila los nodos con `traverse_type` sobre la plantilla `'{}_invocation'` y compone la firma breve `nombre(tipos)` con los tipos de argumento ([`ClassParser.py:945-958`](ClassParser.py:945)).

5.1.31 Se resuelve el receptor de cada invocación en cinco ramas: encadenamiento sobre instanciación propia, `field_access` sobre instanciación, `object_creation_expression`, objeto no declarado en `instance_2_classes` y objeto declarado ([`ClassParser.py:966-1126`](ClassParser.py:966)).

5.1.32 Las invocaciones sin objeto se asocian a `static_imports` y se registran en `static_methods_used`, o se asumen método de la propia clase y se asocian a `this` ([`ClassParser.py:1128-1144`](ClassParser.py:1128)).

5.1.33 Se vuelcan `class_methods_used`, `method_dependencies_by_class`, `external_method_dependencies` y `used_external_dependencies` ordenadas ([`ClassParser.py:1148-1155`](ClassParser.py:1148)).

5.1.34 [`set_method_dependency()`](ClassParser.py:1159) centraliza la inserción con deduplicación por firma breve, almacenando `method_name` y `parameters_list` ([`ClassParser.py:1159-1164`](ClassParser.py:1159)).

5.1.35 [`get_method_m_refs_deps()`](ClassParser.py:1168) recorre los nodos `method_reference`, descarta los de tipo `array_type` y resuelve las referencias por `field_access` con `this` o por `identifier` contra `var_declars`, `class_imports` o `dependent_classes` ([`ClassParser.py:1176-1271`](ClassParser.py:1176)).

5.1.36 [`get_method_f_deps()`](ClassParser.py:1278) recorre los nodos `field_access` descartando `this` y `super`, normaliza el objeto a `this.<campo>`, agrega el campo a `class_fields_used` cuando es de la propia clase y registra `<tipo>.<campo>` como dependencia externa en caso contrario ([`ClassParser.py:1286-1389`](ClassParser.py:1286)).

5.1.37 [`is_getter_or_setter()`](ClassParser.py:811) detecta setters por asignación con `this` a un campo con una única asignación sin `return` ni declaraciones locales, y getters por `return` directo de un campo sin sentencias de expresión ni declaraciones locales ([`ClassParser.py:815-875`](ClassParser.py:815)).

5.1.38 [`test_use_mockito()`](ClassParser.py:660) marca verdadero si algún campo usado está anotado con Mockito, si alguna dependencia externa pertenece a `MOCKITO_CLASSES` o si alguna invocación externa coincide con `Clase.metodo` de `MOCKITO_METHODS` ([`ClassParser.py:661-674`](ClassParser.py:661)).

5.1.39 [`get_class_methods_that_invoke_other_methods()`](ClassParser.py:128) resuelve el método invocador por nombre y aridad y, en caso de empate, compara parámetro a parámetro aceptando equivalencias de wrappers, arreglos de wrappers, tipos genéricos y `unknownType` como coincidencia parcial ([`ClassParser.py:147-246`](ClassParser.py:147)).

5.1.40 Si el invocador retorna un tipo de `java.lang` la invocación se descarta; si retorna el tipo de la clase focal las invocaciones se registran en `class_methods_used`; si retorna una dependencia se registran en `method_dependencies_by_class` y `methods_from_external_dependencies` ([`ClassParser.py:250-284`](ClassParser.py:250)).

5.1.41 Cuando no es posible identificar el invocador las invocaciones se acumulan en `undefined_method_dependencies` ([`ClassParser.py:154-162`](ClassParser.py:154), [286-294](ClassParser.py:286)).

5.1.42 [`traverse_type()`](ClassParser.py:1678), [`children_of_type()`](ClassParser.py:1691), [`get_class_full_signature()`](ClassParser.py:1714) y [`match_from_span()`](ClassParser.py:1733) constituyen las utilidades de navegación y extracción de texto del árbol ([`ClassParser.py:1678-1745`](ClassParser.py:1678)).

5.1.43 [`get_inv_arg_type()`](ClassParser.py:1577) infiere el tipo de cada argumento según el tipo de nodo y etiqueta como `unknownType` los casos no resolubles ([`ClassParser.py:1584-1674`](ClassParser.py:1584)).

5.1.44 [`get_used_static_imports()`](ClassParser.py:796) no presenta invocaciones en el flujo de minería, y [`get_invocations_into_statements()`](ClassParser.py:1502) tiene su llamada comentada ([`ClassParser.py:532`](ClassParser.py:532)).

#### Llamado desde

5.1.45 `ClassParser(language)` se instancia en [`find_map_tests_cases_from_repo.py:322`](find_map_tests_cases_from_repo.py:322) y se recibe por parámetro en el arnés [`test_extract_dependencies()`](find_map_tests_cases_from_repo.py:407), cuya invocación efectiva está comentada ([`find_map_tests_cases_from_repo.py:328`](find_map_tests_cases_from_repo.py:328)).

5.1.46 [`ClassParser.parse_file()`](ClassParser.py:32) se invoca desde [`parse_test_cases()`](find_map_tests_cases_from_repo.py:512) en la línea [516](find_map_tests_cases_from_repo.py:516), desde [`parse_potential_focal_methods()`](find_map_tests_cases_from_repo.py:552) en la línea [556](find_map_tests_cases_from_repo.py:556) y desde [`parse_focal_methods()`](extract_classes_info_d4j.py:335) en la línea [339](extract_classes_info_d4j.py:339) del flujo de evaluación ([`extract_classes_info_d4j.py:339`](extract_classes_info_d4j.py:339)).

5.1.47 Los diccionarios producidos por `ClassParser` son consumidos por [`DependencyParserUtils.parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113), que accede a `class_name`, `imports`, `package`, `fields` y `methods` y a las claves de método `class_fields_used`, `class_method_references_used`, `class_methods_used`, `used_external_dependencies`, `field_dependencies_by_class`, `method_references_dependencies_by_class` y `method_dependencies_by_class` ([`dependency_parser_utils.py:116-122`](dependency_parser_utils.py:116), [139-141](dependency_parser_utils.py:139), [183-209](dependency_parser_utils.py:183)).

5.1.48 `DependencyClassParser` no invoca ningún método de `ClassParser` porque duplica las utilidades como métodos estáticos propios, y la importación prevista permanece comentada ([`DependencyClassParser.py:7`](DependencyClassParser.py:7)).

5.1.49 `ClassParser` importa de [`dependency_parser_utils.py`](dependency_parser_utils.py:4) las constantes `JAVA_LANG_CLASSES_TYPES`, `JAVA_LANG_TYPES_MAPPER`, `MOCKITO_ANNOTATIONS`, `MOCKITO_CLASSES` y `MOCKITO_METHODS`, lo que establece una dependencia circular a nivel de módulo ([`ClassParser.py:7-13`](ClassParser.py:7)).

### 5.2 Script dependency_parser_utils.py : reúne las constantes del dominio, las utilidades de resolución de importaciones y el orquestador que convierte la metadata de `ClassParser` en contexto de dependencias externas efectivamente usadas por cada método focal.

5.2.1 `JAVA_LANG_CLASSES_TYPES` enumera los tipos y envoltorios de `java.lang` excluidos como dependencias, con `Object` comentado y por tanto potencialmente presente como dependencia ([`dependency_parser_utils.py:4-26`](dependency_parser_utils.py:4)).

5.2.2 `JAVA_LANG_TYPES_MAPPER` define la equivalencia entre primitivos y envoltorios, usada para tolerar diferencias de firma ([`dependency_parser_utils.py:28-49`](dependency_parser_utils.py:28)).

5.2.3 `MOCKITO_ANNOTATIONS`, `MOCKITO_CLASSES` y `MOCKITO_METHODS` identifican anotaciones, clases y métodos estáticos de Mockito por nombre simple ([`dependency_parser_utils.py:52-108`](dependency_parser_utils.py:52)).

5.2.4 [`parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113) extrae la lista de nombres de clase presentes en el archivo para detectar clases declaradas en el mismo archivo ([`dependency_parser_utils.py:114`](dependency_parser_utils.py:114)).

5.2.5 Por cada clase parseada se leen `imports`, `package`, `class_name`, `fields` y `methods` ([`dependency_parser_utils.py:116-122`](dependency_parser_utils.py:116)).

5.2.6 Se resuelven las rutas de importación y de paquete con [`get_path_imports()`](dependency_parser_utils.py:433), obteniendo `paths_imports`, `paths_package` e `imports_not_in_project` ([`dependency_parser_utils.py:125`](dependency_parser_utils.py:125)).

5.2.7 Por cada método se leen las tres claves de uso interno producidas por `ClassParser`: `class_fields_used`, `class_method_references_used` y `class_methods_used` ([`dependency_parser_utils.py:139-141`](dependency_parser_utils.py:139)).

5.2.8 Se seleccionan los campos y los métodos de la propia clase usados, ambos con `allow_private = True`, junto con los métodos no resueltos ([`dependency_parser_utils.py:144-148`](dependency_parser_utils.py:144)).

5.2.9 Se compone `used_private_signatures_of_class` con los campos privados usados y las firmas de métodos privados terminadas en `;` ([`dependency_parser_utils.py:150-151`](dependency_parser_utils.py:150)).

5.2.10 Se compone `used_non_private_signatures_of_class` con los campos no privados, las firmas de métodos no privados y los métodos no resueltos, todos terminados en `;` ([`dependency_parser_utils.py:153-156`](dependency_parser_utils.py:153)).

5.2.11 Se construyen `class_private_deps_used` y `class_non_private_deps_used`, que conservan los objetos completos de campo y método (incluidos `modifiers`, `return`, `parameters_list` y `original_string`) y se asignan al método para su consumo por el constructor de corpus ([`dependency_parser_utils.py:158-174`](dependency_parser_utils.py:158)).

5.2.12 Se eliminan del método las claves de minado interno `class_fields_used`, `class_method_references_used` y `class_methods_used` ([`dependency_parser_utils.py:177-179`](dependency_parser_utils.py:177)).

5.2.13 Se inicializan `signatures_of_used_external_dependencies`, como diccionario indexado por firma de clase externa, y `external_dependencies`, como lista de diccionarios ([`dependency_parser_utils.py:185-186`](dependency_parser_utils.py:185)).

5.2.14 Por cada dependencia de `used_external_dependencies` se recopilan los campos usados de `field_dependencies_by_class`, las referencias de `method_references_dependencies_by_class` y las invocaciones de `method_dependencies_by_class`, excluyendo las que ya figuraban como referencias para evitar duplicados ([`dependency_parser_utils.py:188-209`](dependency_parser_utils.py:188)).

5.2.15 Si las tres colecciones están vacías la dependencia se ignora ([`dependency_parser_utils.py:212-217`](dependency_parser_utils.py:212)).

5.2.16 Se normaliza el nombre de la clase externa con [`get_class_name()`](dependency_parser_utils.py:308) y se descartan las referencias a clases internas cuyo nombre resultante contiene `.`, como `Map.Entry` ([`dependency_parser_utils.py:220-223`](dependency_parser_utils.py:220)).

5.2.17 Se resuelve la ruta del archivo externo mediante tres consultas independientes y no excluyentes: `path_import` por nombre de clase en las rutas de los `import`, `path_in_package` por nombre de clase en las rutas del mismo paquete y `path_class` como ruta del propio archivo cuando el nombre externo pertenece a otra clase declarada en el mismo archivo ([`dependency_parser_utils.py:226-257`](dependency_parser_utils.py:226)).

5.2.18 Si `path_import` no es `None` se invoca [`extract_info_from_dependency()`](dependency_parser_utils.py:322) con la ruta del import ([`dependency_parser_utils.py:229-241`](dependency_parser_utils.py:229)).

5.2.19 Si `path_in_package` no es `None` se invoca `extract_info_from_dependency` con la ruta del mismo paquete; ambas invocaciones pueden ejecutarse cuando import y paquete apuntan al mismo archivo, caso en el cual la función deduplica por firma de clase ([`dependency_parser_utils.py:243-255`](dependency_parser_utils.py:243), [380-407](dependency_parser_utils.py:380)).

5.2.20 Si `path_class` no es `None` y el nombre externo está en `classes_in_file`, se invoca `extract_info_from_dependency` con la ruta del propio archivo focal ([`dependency_parser_utils.py:257-269`](dependency_parser_utils.py:257)).

5.2.21 Se asignan al método `signatures_of_external_dependencies` y `external_dependencies` ([`dependency_parser_utils.py:283-284`](dependency_parser_utils.py:283)).

5.2.22 Se eliminan las claves de trabajo `use_some_field`, `var_declars`, `used_external_dependencies`, `methods_from_external_dependencies`, `method_references_from_external_dependencies`, `fields_from_external_dependencies`, `method_dependencies_by_class`, `method_references_dependencies_by_class`, `field_dependencies_by_class`, `undefined_method_dependencies` y `class_methods_that_invoke_other_methods` ([`dependency_parser_utils.py:286-296`](dependency_parser_utils.py:286)).

5.2.23 Se retorna la misma lista `parsed_classes` mutada in situ, sin crear una estructura nueva ([`dependency_parser_utils.py:304`](dependency_parser_utils.py:304)).

5.2.24 [`get_path_imports()`](dependency_parser_utils.py:433) normaliza el paquete eliminando `;` y la palabra `package` y sustituyendo `.` por `/` ([`dependency_parser_utils.py:435`](dependency_parser_utils.py:435)).

5.2.25 Por cada importación se elimina el `;`; si es estática se descarta el último componente y si termina en `*` se registra el paquete en `imports_norm_with_wildcard` ([`dependency_parser_utils.py:440-457`](dependency_parser_utils.py:440)).

5.2.26 Los imports normales se convierten a la forma `paquete/ruta/Clase.java` y se calcula `paths_package` conservando los archivos cuya carpeta termina en el paquete normalizado ([`dependency_parser_utils.py:460-474`](dependency_parser_utils.py:460)).

5.2.27 Se resuelven los imports con comodín y los exactos por sufijo, acumulando en `imports_not_in_project` los paquetes y las clases que no existen en el repositorio, y se fusionan con los resultados con comodín ([`dependency_parser_utils.py:477-522`](dependency_parser_utils.py:477)).

5.2.28 Se calcula la fusión import+paquete dando preferencia a las clases importadas ante homonimia de archivo, aunque el resultado fusionado no se retorna; se retornan tres listas ordenadas `paths_imports`, `paths_package` e `imports_not_in_project` ([`dependency_parser_utils.py:525-542`](dependency_parser_utils.py:525)).

5.2.29 [`extract_info_from_dependency()`](dependency_parser_utils.py:322) invoca [`DependencyClassParser.parse_file()`](DependencyClassParser.py:27) con la ruta, el nombre de la clase externa y el texto de la dependencia ([`dependency_parser_utils.py:332-336`](dependency_parser_utils.py:332)).

5.2.30 Si el parser retorna `None` la extracción termina sin efectos; en caso contrario se usa la firma de la clase externa como clave del diccionario de firmas ([`dependency_parser_utils.py:344-348`](dependency_parser_utils.py:344)).

5.2.31 Se filtran los campos usados contra los campos reales de la clase externa con `allow_private = False` y se agregan sus cadenas originales sin duplicar ([`dependency_parser_utils.py:350-355`](dependency_parser_utils.py:350)).

5.2.32 Se agregan los constructores no privados de la clase externa con independencia de si fueron invocados explícitamente ([`dependency_parser_utils.py:358-361`](dependency_parser_utils.py:358)).

5.2.33 Se resuelven los métodos usados mediante [`get_methods_from_external_dependency()`](dependency_parser_utils.py:560) y se agregan las firmas resueltas y los métodos no resueltos, ambos terminados en `;` ([`dependency_parser_utils.py:364-377`](dependency_parser_utils.py:364)).

5.2.34 Si ya existe una entrada con la misma firma de clase se fusionan campos y métodos evitando duplicados por `original_string` y por `full_signature_parameters`, y se extienden los métodos no resueltos ([`dependency_parser_utils.py:380-407`](dependency_parser_utils.py:380)).

5.2.35 Si no existe se agrega un diccionario con `class_name`, `external_dependency`, `superclass`, `interfaces`, `class_signature`, `has_constructor`, `fields`, `methods` y `undefined_methods` ([`dependency_parser_utils.py:410-425`](dependency_parser_utils.py:410)).

5.2.36 [`get_methods_from_external_dependency()`](dependency_parser_utils.py:560) resuelve por nombre cuando el nombre de un método externo aparece en las referencias usadas, respetando la restricción de privacidad ([`dependency_parser_utils.py:568-572`](dependency_parser_utils.py:568)).

5.2.37 Se resuelve por firma filtrando cada invocación por nombre, privacidad y aridad; la invocación se marca como no resuelta en `undefined_methods_from_dependency` cuando no hay coincidencia ([`dependency_parser_utils.py:578-599`](dependency_parser_utils.py:578)).

5.2.38 Si existe exactamente una coincidencia se agrega mediante [`add_method_matching()`](dependency_parser_utils.py:688); si existen varias se comparan parámetro a parámetro aceptando equivalencia de envoltorios, arreglos de envoltorios, tipos genéricos con el mismo tipo base y `unknownType` como coincidencia parcial ([`dependency_parser_utils.py:601-664`](dependency_parser_utils.py:601)).

5.2.39 Se agrega la primera coincidencia total, se marcan las parciales y, si ninguna coincide, la invocación se marca como no resuelta ([`dependency_parser_utils.py:666-682`](dependency_parser_utils.py:666)).

5.2.40 [`add_method_matching()`](dependency_parser_utils.py:688) deduplica por la cadena `parameters` del método ([`dependency_parser_utils.py:689-696`](dependency_parser_utils.py:689)).

5.2.41 [`get_used_fields_from_external_dependency()`](dependency_parser_utils.py:546) conserva los campos cuyo `var_name` figura en la lista de campos usados y que cumplen la restricción de privacidad ([`dependency_parser_utils.py:549-556`](dependency_parser_utils.py:549)).

5.2.42 [`get_class_name()`](dependency_parser_utils.py:308) elimina sufijos de arreglo y de tipo genérico para obtener el nombre base, y [`get_path_import_by_class_name()`](dependency_parser_utils.py:314) retorna la primera ruta que termina en `/<Clase>.java` ([`dependency_parser_utils.py:309-318`](dependency_parser_utils.py:309)).

#### Llamado desde

5.2.43 [`parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113) se invoca desde [`parse_potential_focal_methods()`](find_map_tests_cases_from_repo.py:552) en la línea [558](find_map_tests_cases_from_repo.py:558) y desde [`parse_focal_methods()`](extract_classes_info_d4j.py:335) en la línea [340](extract_classes_info_d4j.py:340); su invocación alternativa dentro del arnés de depuración está comentada ([`find_map_tests_cases_from_repo.py:443`](find_map_tests_cases_from_repo.py:443)).

5.2.44 [`get_methods_from_external_dependency()`](dependency_parser_utils.py:560) se invoca desde [`match_test_cases()`](find_map_tests_cases_from_repo.py:581) en la línea [648](find_map_tests_cases_from_repo.py:648) y desde [`extract_info_from_dependency()`](dependency_parser_utils.py:322) en la línea [364](dependency_parser_utils.py:364).

5.2.45 [`get_class_name()`](dependency_parser_utils.py:308) se invoca desde [`match_test_cases()`](find_map_tests_cases_from_repo.py:581) en las líneas [634](find_map_tests_cases_from_repo.py:634) y [640](find_map_tests_cases_from_repo.py:640), y desde [`parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113) en la línea [220](dependency_parser_utils.py:220).

5.2.46 [`extract_info_from_dependency()`](dependency_parser_utils.py:322) se invoca únicamente desde [`parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113) en las líneas [231](dependency_parser_utils.py:231), [245](dependency_parser_utils.py:245) y [259](dependency_parser_utils.py:259).

5.2.47 `DependencyParserUtils` se instancia como contenedor de métodos estáticos en [`find_map_tests_cases_from_repo.py:324`](find_map_tests_cases_from_repo.py:324) y en [`extract_classes_info_d4j.py:211`](extract_classes_info_d4j.py:211), y se propaga como parámetro a `parse_potential_focal_methods` y `match_test_cases` ([`find_map_tests_cases_from_repo.py:346`](find_map_tests_cases_from_repo.py:346)).

5.2.48 El contexto dinámico externo se materializa en dos formas complementarias: `signatures_of_external_dependencies`, mapa firma de clase→firmas usadas, y `external_dependencies`, lista estructurada consumida por el constructor del corpus ([`dependency_parser_utils.py:283-284`](dependency_parser_utils.py:283)).

### 5.3 Script DependencyClassParser.py : parser especializado en clases externas que localiza una clase concreta dentro de un archivo y extrae solo metadatos de firma.

5.3.1 No existe relación de herencia: la cabecera declara `class DependencyClassParser():` sin clase base ([`DependencyClassParser.py:10`](DependencyClassParser.py:10)).

5.3.2 La importación de utilidades compartidas está prevista pero comentada, lo que confirma la duplicación deliberada de código ([`DependencyClassParser.py:7`](DependencyClassParser.py:7)).

5.3.3 [`__init__()`](DependencyClassParser.py:12) reproduce la lógica de compatibilidad de versiones de `tree-sitter` ([`DependencyClassParser.py:13-24`](DependencyClassParser.py:13)).

5.3.4 [`parse_file()`](DependencyClassParser.py:27) recibe tres argumentos: ruta del archivo, nombre de la clase buscada y texto de la dependencia externa ([`DependencyClassParser.py:27-30`](DependencyClassParser.py:27)).

5.3.5 Ante fallo de lectura se retorna `None`, a diferencia de `ClassParser`, que retorna lista vacía ([`DependencyClassParser.py:39-44`](DependencyClassParser.py:39)).

5.3.6 Se parsea el contenido y, si el árbol presenta errores, se retorna `None` ([`DependencyClassParser.py:55-62`](DependencyClassParser.py:55)).

5.3.7 Se reúnen las declaraciones de clase y de interfaz, a diferencia de `ClassParser`, que solo considera clases ([`DependencyClassParser.py:64-66`](DependencyClassParser.py:64)).

5.3.8 Se recorre cada declaración descartando las que no coinciden con el nombre solicitado ([`DependencyClassParser.py:68-72`](DependencyClassParser.py:68)).

5.3.9 Se obtiene la metadata de clase con `external_dependency` incluido ([`DependencyClassParser.py:74`](DependencyClassParser.py:74)).

5.3.10 Se recorren los hijos de `class_body` o `interface_body` para obtener la metadata de cada método con [`get_function_metadata()`](DependencyClassParser.py:207) y se retorna la primera clase coincidente ([`DependencyClassParser.py:78-99`](DependencyClassParser.py:78)).

5.3.11 Si ninguna declaración coincide se retorna `None` ([`DependencyClassParser.py:101`](DependencyClassParser.py:101)).

5.3.12 El diccionario de clase incorpora la clave `external_dependency` y no incluye `imports`, `package`, `argument_list` ni `class_methods_that_invoke_other_methods`, porque no se realiza análisis de cuerpo ([`DependencyClassParser.py:109-119`](DependencyClassParser.py:109)).

5.3.13 El diccionario de campo omite `field_use_mockito_annotations` respecto de `ClassParser` ([`DependencyClassParser.py:166-201`](DependencyClassParser.py:166)).

5.3.14 El diccionario de método conserva solo las claves de firma `method_name`, `parameters`, `parameters_list`, `modifiers`, `type_parameters`, `return`, `class`, `signature`, `full_signature`, `full_signature_parameters`, `class_method_signature` e `is_constructor` ([`DependencyClassParser.py:213-226`](DependencyClassParser.py:213)).

5.3.15 [`parse_parameters()`](DependencyClassParser.py:311) retorna únicamente la lista de tipos, sin mapa instancia→clase ni lista de clases dependientes ([`DependencyClassParser.py:355-358`](DependencyClassParser.py:355)).

5.3.16 [`get_class_full_signature()`](DependencyClassParser.py:397) y [`match_from_span()`](DependencyClassParser.py:416) replican la implementación de `ClassParser` ([`DependencyClassParser.py:401-412`](DependencyClassParser.py:401)).

#### Llamado desde

5.3.17 `DependencyClassParser(language)` se instancia en [`find_map_tests_cases_from_repo.py:323`](find_map_tests_cases_from_repo.py:323) y en [`extract_classes_info_d4j.py:210`](extract_classes_info_d4j.py:210), y se propaga como parámetro a través de `parse_potential_focal_methods` y `parse_potential_focal_and_external_dependencies` ([`find_map_tests_cases_from_repo.py:346`](find_map_tests_cases_from_repo.py:346)).

5.3.18 [`DependencyClassParser.parse_file()`](DependencyClassParser.py:27) se invoca exclusivamente desde [`DependencyParserUtils.extract_info_from_dependency()`](dependency_parser_utils.py:322) en la línea [332](dependency_parser_utils.py:332).

### 5.4 Script ParserUtils.py : reúne las utilidades de validación sintáctica y de limpieza textual aplicadas sobre fragmentos de código, en el post-procesamiento del corpus.

5.4.1 [`__init__()`](ParserUtils.py:13) reproduce la lógica de compatibilidad de versiones de `tree-sitter` y almacena `input_encoding`, fijando el nombre de lenguaje literalmente como `"java"` cuando la versión es anterior a `0.22.0` ([`ParserUtils.py:14-27`](ParserUtils.py:14)).

5.4.2 [`validate_if_code_has_errors()`](ParserUtils.py:30) codifica el fragmento con `input_encoding` y lo parsea ([`ParserUtils.py:31-36`](ParserUtils.py:31)).

5.4.3 Si `validate_all_errors` es verdadero se retorna directamente `root_node.has_error` ([`ParserUtils.py:38-39`](ParserUtils.py:38)).

5.4.4 En modo tolerante se recopilan los nodos faltantes con [`traverse_tree_missing()`](ParserUtils.py:381) y los nodos de error con [`traverse_tree_only_errors()`](ParserUtils.py:389) ([`ParserUtils.py:41-45`](ParserUtils.py:41)).

5.4.5 Si todos los faltantes son de tipo `identifier` y no hay nodos de error el fragmento se considera válido; en cualquier otro caso se retorna `has_error` ([`ParserUtils.py:47-63`](ParserUtils.py:47)).

5.4.6 [`method_body_is_empty()`](ParserUtils.py:66) parsea el fragmento, toma el primer hijo del nodo raíz como declaración y retorna verdadero si no hay hijos, si no hay nodo `body`, si el texto del cuerpo está vacío o si el contenido entre llaves está vacío ([`ParserUtils.py:70-98`](ParserUtils.py:70)).

5.4.7 [`clean_comments()`](ParserUtils.py:101) sustituye cada `block_comment` por un espacio y elimina los `line_comment` ordenados por longitud descendente, para evitar que un comentario prefijo impida eliminar otro más largo que lo contiene ([`ParserUtils.py:133-163`](ParserUtils.py:133)).

5.4.8 [`clean_annotations()`](ParserUtils.py:173) recopila los nodos `annotation` y `marker_annotation`, los ordena por longitud descendente y los elimina, retornando el código sin anotaciones ni espacios sobrantes ([`ParserUtils.py:187-217`](ParserUtils.py:187)).

5.4.9 [`clean_signatures_annotations()`](ParserUtils.py:220) recorre la primera declaración de método y elimina las anotaciones de sus modificadores recortando por desplazamientos de bytes y acumulando la reducción de longitud, para luego colapsar espacios múltiples ([`ParserUtils.py:237-273`](ParserUtils.py:237)).

5.4.10 [`fix_close_type_parameter_sig_class()`](ParserUtils.py:277) agrega `" { }"` a la firma para forzar un parseo válido, inserta cada `>` faltante compensando el desplazamiento acumulado y elimina las llaves auxiliares ([`ParserUtils.py:283-309`](ParserUtils.py:283)).

5.4.11 [`fix_type_parameters_inconsistences()`](ParserUtils.py:314) recopila los nodos de error y, cuando el primer hijo del nodo de error es de tipo `type_parameters`, elimina ese fragmento por desplazamiento de bytes y colapsa espacios, corrigiendo duplicaciones del estilo `public<T> <T> Constructor()` ([`ParserUtils.py:332-358`](ParserUtils.py:332)).

5.4.12 [`get_body_methods_from_class()`](ParserUtils.py:361) parsea el código y retorna el conjunto de los textos completos normalizados de todas las `method_declaration` ([`ParserUtils.py:361-376`](ParserUtils.py:361)).

5.4.13 [`traverse_type()`](ParserUtils.py:397), [`children_of_type()`](ParserUtils.py:410) y [`match_from_span()`](ParserUtils.py:432) replican la implementación de `ClassParser` ([`ParserUtils.py:397-444`](ParserUtils.py:397)).

#### Llamado desde

5.4.14 `ParserUtils` no es importado ni invocado por `find_map_tests_cases_from_repo.py`: `ClassParser` y `DependencyClassParser` mantienen copias propias de las utilidades de navegación ([`ParserUtils.py:397-444`](ParserUtils.py:397)).

5.4.15 `ParserUtils` se importa en [`build_corpus.py:8`](build_corpus.py:8) y se instancia en [`build_corpus.py:817`](build_corpus.py:817), y se importa en [`build_corpus_d4j.py:9`](build_corpus_d4j.py:9) e instancia en [`build_corpus_d4j.py:100`](build_corpus_d4j.py:100) ([`build_corpus_d4j.py:100`](build_corpus_d4j.py:100)).

5.4.16 `ParserUtils` se importa y se instancia en las validaciones de datasets: [`validate_d4j_in_CodeSearchNet.py:10`](validate_d4j_in_CodeSearchNet.py:10) con instanciación en la línea [139](validate_d4j_in_CodeSearchNet.py:139), y [`validate_d4j_in_GithubCode.py:10`](validate_d4j_in_GithubCode.py:10) con instanciación en la línea [147](validate_d4j_in_GithubCode.py:147).

5.4.17 [`clean_comments()`](ParserUtils.py:101) se consume desde [`build_corpus.py:656`](build_corpus.py:656), [`build_corpus_d4j.py:602`](build_corpus_d4j.py:602), [`validate_d4j_in_CodeSearchNet.py:49`](validate_d4j_in_CodeSearchNet.py:49) y [`validate_d4j_in_GithubCode.py:49`](validate_d4j_in_GithubCode.py:49); [`clean_annotations()`](ParserUtils.py:173) desde [`build_corpus.py:670`](build_corpus.py:670) y [`build_corpus_d4j.py:616`](build_corpus_d4j.py:616); y [`clean_signatures_annotations()`](ParserUtils.py:220) desde [`build_corpus.py:675`](build_corpus.py:675) y [`build_corpus_d4j.py:621`](build_corpus_d4j.py:621).

5.4.18 [`validate_if_code_has_errors()`](ParserUtils.py:30) se consume desde [`build_corpus.py:370`](build_corpus.py:370), [381](build_corpus.py:381), [439](build_corpus.py:439), [529](build_corpus.py:529), [549](build_corpus.py:549) y [589](build_corpus.py:589), y desde [`build_corpus_d4j.py:344`](build_corpus_d4j.py:344), [395](build_corpus_d4j.py:395), [475](build_corpus_d4j.py:475), [495](build_corpus_d4j.py:495) y [536](build_corpus_d4j.py:536).

5.4.19 [`method_body_is_empty()`](ParserUtils.py:66) se consume desde [`build_corpus.py:360-361`](build_corpus.py:360) y [`build_corpus_d4j.py:338`](build_corpus_d4j.py:338); [`fix_type_parameters_inconsistences()`](ParserUtils.py:314) desde [`build_corpus.py:354`](build_corpus.py:354) y [`build_corpus_d4j.py:336`](build_corpus_d4j.py:336); [`fix_close_type_parameter_sig_class()`](ParserUtils.py:277) desde [`build_corpus.py:524`](build_corpus.py:524) y [`build_corpus_d4j.py:472`](build_corpus_d4j.py:472); y [`get_body_methods_from_class()`](ParserUtils.py:361) desde [`validate_d4j_in_CodeSearchNet.py:292`](validate_d4j_in_CodeSearchNet.py:292).

---

## 6) Flujo de construcción del corpus de evaluación Defects4J

El corpus de evaluación se diferencia del flujo principal en tres puntos estructurales: no existe trazabilidad test ↔ método focal, las clases a procesar se reciben de forma explícita y existe una secuencia previa obligatoria de comandos sobre el framework de Defects4J ([`extract_classes_info_d4j.py:335`](extract_classes_info_d4j.py:335), [221-250](extract_classes_info_d4j.py:221), [`DEFECTS4J_README.md:32`](DEFECTS4J_README.md:32)).

### 6.1 Prerrequisitos y scripts de la carpeta `d4j_utils`

6.1.1 **Entorno.** Se requiere Defects4J `2.0.1` instalado o la imagen `eljavatar/d4j_tests_benchmark:version11` ([`DEFECTS4J_README.md:36`](DEFECTS4J_README.md:36), [38-42](DEFECTS4J_README.md:38)).

6.1.2 **Dependencias Python.** Se requieren Python `>= 3.9`, Git `>= 2.34` y los paquetes `pandas`, `scikit-learn`, `packaging`, `command-runner`, `GitPython`, `tree-sitter==0.21.0` y `tree-sitter-java==0.21.0` ([`DEFECTS4J_README.md:49`](DEFECTS4J_README.md:49), [52](DEFECTS4J_README.md:52)).

6.1.3 **Colocación de los scripts.** Se crea `/defects4j/framework/custom` y se copia allí el contenido de `d4j_utils/`, condición necesaria además para que el Perl encuentre `../core` ([`DEFECTS4J_README.md:63`](DEFECTS4J_README.md:63), [`build_csv_corpus_d4j.pl:15-17`](d4j_utils/build_csv_corpus_d4j.pl:15)).

6.1.4 **Paso 1 — exportar revisiones.** [`export_revisions.sh`](d4j_utils/export_revisions.sh:1) declara la lista de los 17 proyectos Defects4J (`Closure`, `Cli`, `Codec`, `Collections`, `Compress`, `Csv`, `JxPath`, `Lang`, `Math`, `Gson`, `JacksonCore`, `JacksonDatabind`, `JacksonXml`, `Chart`, `Time`, `Jsoup`, `Mockito`), con las variantes reducidas comentadas ([`export_revisions.sh:3`](d4j_utils/export_revisions.sh:3), [4-6](d4j_utils/export_revisions.sh:4)).

6.1.5 Se fija `revisions_dir=/defects4j_revisions` y `repo_type=f`, correspondiente a la versión con el bug corregido; la ruta de Windows usada en desarrollo permanece comentada ([`export_revisions.sh:9-11`](d4j_utils/export_revisions.sh:9)).

6.1.6 Por cada proyecto se consultan los identificadores de bug con `defects4j query -p ${repo} -q "bug.id"` ([`export_revisions.sh:17-18`](d4j_utils/export_revisions.sh:17)).

6.1.7 Por cada identificador se compone `repo_name=${repo}_${id}_${repo_type}` y `repo_path=${revisions_dir}/${repo_name}` ([`export_revisions.sh:20-21`](d4j_utils/export_revisions.sh:20)).

6.1.8 La descarga se ejecuta con `defects4j checkout -p $repo -v ${id}${repo_type} -w ${revisions_dir}/${repo_name}`; la barra `|| continue` omite un fallo de checkout sin registro y sin abortar el proyecto ([`export_revisions.sh:22`](d4j_utils/export_revisions.sh:22)).

6.1.9 La revisión se compila con `cd $repo_name && defects4j compile`, con `cd` relativo porque el bucle ya se encuentra en `revisions_dir` ([`export_revisions.sh:23`](d4j_utils/export_revisions.sh:23)).

6.1.10 **Paso 2 — exportar clases focales.** [`export_focal_classes.sh`](d4j_utils/export_focal_classes.sh:1) reutiliza la misma lista de 17 proyectos y la marca `repo_type=f` ([`export_focal_classes.sh:3`](d4j_utils/export_focal_classes.sh:3), [7](d4j_utils/export_focal_classes.sh:7)).

6.1.11 Por cada proyecto se consultan las clases modificadas al corregir cada bug con `defects4j query -p ${repo} -q "classes.modified"` ([`export_focal_classes.sh:14`](d4j_utils/export_focal_classes.sh:14)).

6.1.12 La salida se normaliza eliminando comillas y se itera registro por registro, tomando el campo 1 como identificador de bug y el campo 2 como lista de clases separadas por `;` ([`export_focal_classes.sh:15-18`](d4j_utils/export_focal_classes.sh:15)).

6.1.13 La lista de clases se convierte en array JSON con `jq -R -s -c 'split(";")'` y se compone la clave de revisión `revision=${repo}_${bugid}_${repo_type}`, acumulando el objeto `{"project": ..., "classes": [...]}` con `jq` ([`export_focal_classes.sh:20-23`](d4j_utils/export_focal_classes.sh:20)).

6.1.14 El resultado se escribe como `focal_classes.json` en el directorio de trabajo actual, es decir `/defects4j/framework/custom/focal_classes.json` ([`export_focal_classes.sh:26`](d4j_utils/export_focal_classes.sh:26)).

6.1.15 El esquema producido es un array de objetos con `project` (cadena `{Proyecto}_{bugId}_f`) y `classes` (array de nombres plenamente calificados); el paso 3 consume solo estas dos claves ([`extract_classes_info_d4j.py:222-224`](extract_classes_info_d4j.py:222), [550](extract_classes_info_d4j.py:550)).

6.1.16 **Paso 5 — generar el CSV.** [`build_all_csv_corpus_d4j.sh`](d4j_utils/build_all_csv_corpus_d4j.sh:1) parsea cuatro opciones: `-s` scaffoldings, `-d` datos del corpus, `-o` salida CSV y `-t` directorio temporal de checkouts ([`build_all_csv_corpus_d4j.sh:14-33`](d4j_utils/build_all_csv_corpus_d4j.sh:14)); las opciones desconocidas invocan `usage`, que no está definida en el archivo ([`build_all_csv_corpus_d4j.sh:24-31`](d4j_utils/build_all_csv_corpus_d4j.sh:24)).

6.1.17 Se reutiliza la lista de 17 proyectos y se invoca el Perl una vez por proyecto, pasando `-s` solo si `scaffoldings_dir` está definido; la invocación documentada no usa `-s`, por lo que `USE_SCAFFOLDING` queda desactivado ([`build_all_csv_corpus_d4j.sh:3`](d4j_utils/build_all_csv_corpus_d4j.sh:3), [45-61](d4j_utils/build_all_csv_corpus_d4j.sh:45)).

6.1.18 [`build_csv_corpus_d4j.pl`](d4j_utils/build_csv_corpus_d4j.pl:1) declara las opciones `p:v:t:s:d:o:S`, con `-p` obligatorio, `-v` opcional para restringir a una versión, `-s` raíz de scaffoldings, `-d` raíz de datos, `-o` directorio CSV, `-S` activación de generación mediante scaffoldings y `-t` directorio temporal ([`build_csv_corpus_d4j.pl:21-31`](d4j_utils/build_csv_corpus_d4j.pl:21)).

6.1.19 Se crea el objeto de proyecto con `Project::create_project($PID)`, se le asigna el directorio temporal como raíz y se derivan `$project_dir` y `$path_input_corpus` ([`build_csv_corpus_d4j.pl:34-39`](d4j_utils/build_csv_corpus_d4j.pl:34)).

6.1.20 Las versiones a procesar son las de `-v` o, en su defecto, todos los bugs del proyecto; por cada versión se forma `vid="${id}f"` y, con scaffolding, se exige el archivo `${PID}-${vid}-scaffolding.tar.bz2` ([`build_csv_corpus_d4j.pl:49-76`](d4j_utils/build_csv_corpus_d4j.pl:49)).

6.1.21 Se cargan las clases modificadas del framework con `open(IN, "<${project_dir}/modified_classes/${id}.src")` y se omite la versión con aviso si no existe `${path_data}/${PID}/${id}/methods` ([`build_csv_corpus_d4j.pl:79-95`](d4j_utils/build_csv_corpus_d4j.pl:79)).

6.1.22 Se recorre cada subcarpeta de método y se decodifica `${path_methods}/${method_number}/corpus.json` ([`build_csv_corpus_d4j.pl:99-137`](d4j_utils/build_csv_corpus_d4j.pl:99)).

6.1.23 El emparejamiento se realiza por nombre simple de clase: se deriva `focal_class_name` del último punto del nombre calificado y se compara con el nombre de archivo de `path_focal_class` contenido en `corpus.json` ([`build_csv_corpus_d4j.pl:141-188`](d4j_utils/build_csv_corpus_d4j.pl:141)).

6.1.24 Se construye una fila por método aceptado con `id`, `project`, `version`, `number_method_by_version`, `modified_class`, `focal_method`, `focal_class`, `path_focal_class_in_project`, `test_class`, `path_test_class`, `package_focal_class`, `imports_focal_class`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx` y `src_fm_fc_dctx_priv` ([`build_csv_corpus_d4j.pl:198-216`](d4j_utils/build_csv_corpus_d4j.pl:198)).

6.1.25 La clase de prueba se nombra por convención `${focal_class_name}Test` con ruta `${file_class}Test.java`, o `${focal_class_name}_ESTest` y `${file_class}_ESTest.java` cuando se usa scaffolding ([`build_csv_corpus_d4j.pl:151-160`](d4j_utils/build_csv_corpus_d4j.pl:151)).

6.1.26 Las filas se ordenan por `version` y luego por `number_method_by_version` y se escriben en `${out_dir}/${PID}_methods.csv` con `Text::CSV` en modo `binary`; las 15 columnas se declaran antes de la escritura y el directorio temporal se elimina al final ([`build_csv_corpus_d4j.pl:227-267`](d4j_utils/build_csv_corpus_d4j.pl:227), [270](d4j_utils/build_csv_corpus_d4j.pl:270)).

6.1.27 Filtro efectivo del CSV: solo se emiten métodos cuya clase focal figure en `modified_classes/{id}.src`, por lo que un método focal de una clase no registrada como modificada desaparece del CSV sin aviso ([`build_csv_corpus_d4j.pl:80-85`](d4j_utils/build_csv_corpus_d4j.pl:80), [141](d4j_utils/build_csv_corpus_d4j.pl:141)).

6.1.28 **Entrada externa del paso 3.** `test_and_src_paths_by_project.json` se declara como `--test_and_src_paths_json_file`, se carga de forma incondicional y espera un diccionario indexado por `{proyecto}_{version}` en minúsculas y sin sufijo `_f`/`_b`, con al menos la clave `src` ([`extract_classes_info_d4j.py:498-504`](extract_classes_info_d4j.py:498), [230-235](extract_classes_info_d4j.py:230)). Ningún script del repositorio genera este archivo (a confirmar su procedencia exacta); su ausencia aborta la ejecución en la línea [553](extract_classes_info_d4j.py:553).

6.1.29 **Orden estricto de la secuencia.** El paso 2 consume el framework operativo, el paso 3 consume `focal_classes.json`, el paso 4 consume la carpeta `mining` y el paso 5 consume `data_by_project_and_version` ([`extract_classes_info_d4j.py:548`](extract_classes_info_d4j.py:548), [`build_corpus_d4j.py:724`](build_corpus_d4j.py:724), [`build_all_csv_corpus_d4j.sh:58`](d4j_utils/build_all_csv_corpus_d4j.sh:58)).

### 6.2 Script extract_classes_info_d4j.py : recorre las revisiones exportadas de Defects4J y, para cada clase focal indicada explícitamente, extrae los métodos focales con su contexto focal y dinámico, exportando un JSON por método, sin clase de prueba en ninguna etapa.

6.2.1 Se importan las dependencias del sistema y las tres piezas del analizador: [`ClassParser`](extract_classes_info_d4j.py:16), [`DependencyClassParser`](extract_classes_info_d4j.py:17) y [`DependencyParserUtils`](extract_classes_info_d4j.py:20); no se leen credenciales de GitHub ([`extract_classes_info_d4j.py:1-20`](extract_classes_info_d4j.py:1)).

6.2.2 [`parse_args()`](extract_classes_info_d4j.py:473) define siete parámetros: `--repos_path`, `--project_id`, `--focal_classes_json_file`, `--test_and_src_paths_json_file`, `--extract_only_focal_classes`, `--output` y `--output_empty` ([`extract_classes_info_d4j.py:477-525`](extract_classes_info_d4j.py:477)).

6.2.3 `--extract_only_focal_classes` se declara con `type=bool` y valor por defecto `True`, de modo que cualquier cadena no vacía produce `True` y solo la cadena vacía produce `False` ([`extract_classes_info_d4j.py:505-511`](extract_classes_info_d4j.py:505)).

6.2.4 Se retorna `vars(parser.parse_args())` como diccionario ([`extract_classes_info_d4j.py:527`](extract_classes_info_d4j.py:527)).

6.2.5 Si `extract_only_focal_classes` es verdadero se validan las rutas y se carga el JSON de clases focales con `json.load`; las comprobaciones usan `raise` con un literal de cadena, que en Python 3 produce `TypeError` en lugar del mensaje previsto ([`extract_classes_info_d4j.py:542-549`](extract_classes_info_d4j.py:542), [544](extract_classes_info_d4j.py:544)).

6.2.6 Se construye `list_projects_version_names` con la clave `project` de cada entrada y se carga siempre el JSON de rutas de src y test, sin comprobación previa de existencia ([`extract_classes_info_d4j.py:550-554`](extract_classes_info_d4j.py:550)).

6.2.7 Se fija la lista literal de 17 proyectos y se inicializa `projects_paths` según `project_id`; un identificador distinto de `all` y fuera de la lista aborta con `raise` de cadena ([`extract_classes_info_d4j.py:557-568`](extract_classes_info_d4j.py:557)).

6.2.8 Se recorre el primer nivel de `repos_path` con `next(os.walk(...))[1]`, descartando las revisiones que no figuran en `focal_classes.json`, y el nombre del proyecto se obtiene cortando la revisión por `_` ([`extract_classes_info_d4j.py:572-581`](extract_classes_info_d4j.py:572)).

6.2.9 Se delega en [`analyze_projects()`](extract_classes_info_d4j.py:438), que crea un `Pool` por proyecto e itera con `imap_unordered` sobre [`analyze_project_wrapper()`](extract_classes_info_d4j.py:433), transfiriendo a cada proceso la tupla completa con el contenido de `focal_classes.json` ([`extract_classes_info_d4j.py:447-462`](extract_classes_info_d4j.py:447)).

6.2.10 [`analyze_project()`](extract_classes_info_d4j.py:39) deriva `project_name_version` del nombre base de la ruta y crea `{output}/{project_name_version}` con `os.makedirs`, sin carpeta intermedia por `project_id` ([`extract_classes_info_d4j.py:50-65`](extract_classes_info_d4j.py:50)).

6.2.11 Se invoca [`find_focal_classes()`](extract_classes_info_d4j.py:101) con el lenguaje fijo `'java'` y se desempaqueta la tupla `(tot_fclasses, tot_mfm_by_focal, tot_mfm, repo_exists, error_finding_java_files)` ([`extract_classes_info_d4j.py:68-79`](extract_classes_info_d4j.py:68)).

6.2.12 Si no se extrajo ningún método focal se listan los archivos del directorio y se copian al subdirectorio de clasificación con [`copy_error_files()`](extract_classes_info_d4j.py:32): `1_repo_not_exists/` si la ruta no existe, `2_error_finding_java_files/` si falló el inventario Java y `3_not_mapping_focal_methods/` en el resto ([`extract_classes_info_d4j.py:81-89`](extract_classes_info_d4j.py:81)).

6.2.13 El directorio de la revisión se elimina con `shutil.rmtree(..., ignore_errors=True)` tras clasificar el fallo, de modo que las revisiones sin resultados no dejan rastro en `--output` ([`extract_classes_info_d4j.py:91`](extract_classes_info_d4j.py:91)).

6.2.14 [`find_focal_classes()`](extract_classes_info_d4j.py:101) abre `{output}/log.txt`, escribe la cabecera con `project_id` y revisión, e inicializa `repo_exists = True` y `error_finding_java_files = False` ([`extract_classes_info_d4j.py:113-119`](extract_classes_info_d4j.py:113)).

6.2.15 Si la ruta de la revisión existe se cambia el directorio de trabajo a ella; en caso contrario se registra en el log y se retorna `0, 0, 0, False, True` ([`extract_classes_info_d4j.py:122-129`](extract_classes_info_d4j.py:122)).

6.2.16 Se detectan los archivos con `@Test` mediante `subprocess.check_output(r'grep -l -r @Test --include \*.java', shell=True)` y decodificación ASCII; los errores de `grep` se registran pero la marca de error está comentada, por lo que `tests` queda vacío y el flujo continúa ([`extract_classes_info_d4j.py:132-155`](extract_classes_info_d4j.py:132)).

6.2.17 Se inventarían los archivos Java con `glob.glob('**/*.java', recursive=True)`, normalizando barras y eliminando el prefijo `./`; este es el único punto que activa `error_finding_java_files` y retorna la tupla de ceros ([`extract_classes_info_d4j.py:162-184`](extract_classes_info_d4j.py:162)).

6.2.18 El conjunto de clases focales candidatas es la diferencia entre todos los `.java` y los archivos de test, descartando las rutas con `src/test`; este conjunto actúa como universo para resolver dependencias y no como fuente de las clases a procesar ([`extract_classes_info_d4j.py:190-192`](extract_classes_info_d4j.py:190)).

6.2.19 Se instancian `ClassParser(language)`, `DependencyClassParser(language)` y `DependencyParserUtils()` y se abre `log_error_mapping.txt` ([`extract_classes_info_d4j.py:209-219`](extract_classes_info_d4j.py:209)).

6.2.20 Se seleccionan las clases de la revisión desde `focal_classes_content` comparando `repo['project']` con `project_name_version`; sin coincidencia la lista queda vacía y el resultado se clasifica como `3_not_mapping_focal_methods/` ([`extract_classes_info_d4j.py:221-224`](extract_classes_info_d4j.py:221)).

6.2.21 Se deriva la clave de búsqueda en el JSON de rutas quitando los sufijos `_f` y `_b` y pasando a minúsculas, y se obtiene la ruta `src` ([`extract_classes_info_d4j.py:230-235`](extract_classes_info_d4j.py:230)).

6.2.22 Por cada nombre de clase explícito se construye la ruta relativa convirtiendo puntos en barras, se antepone `src` y se localiza el archivo con [`get_class_path()`](extract_classes_info_d4j.py:23); las clases no encontradas se omiten con `continue` sin registro ([`extract_classes_info_d4j.py:238-250`](extract_classes_info_d4j.py:238)).

6.2.23 Se itera sobre todas las clases focales candidatas con `tqdm` y se filtra por coincidencia de subcadena entre la ruta candidata y alguna de las rutas explícitas ([`extract_classes_info_d4j.py:256-268`](extract_classes_info_d4j.py:256)).

6.2.24 Para las clases conservadas se invoca [`parse_focal_methods()`](extract_classes_info_d4j.py:335) y [`get_mapped_focal_methods()`](extract_classes_info_d4j.py:372), y se guarda la lista cuando no está vacía ([`extract_classes_info_d4j.py:274-288`](extract_classes_info_d4j.py:274)).

6.2.25 Cualquier excepción se registra en ambos logs y se re-lanza, de modo que un solo fallo aborta la revisión y, por propagación a través del pool, la ejecución completa ([`extract_classes_info_d4j.py:289-301`](extract_classes_info_d4j.py:289)).

6.2.26 Si existen resultados se exportan con [`export_mfm()`](extract_classes_info_d4j.py:385) y se copian las clases focales a `{output}/focal_classes/`, carpeta que consume [`build_corpus_d4j.py`](build_corpus_d4j.py:142) ([`extract_classes_info_d4j.py:306-314`](extract_classes_info_d4j.py:306)).

6.2.27 Se escribe el resumen en `log.txt`, se cierran ambos logs, se elimina `log_error_mapping.txt` si no hubo errores y se retorna `(tot_fclasses, len(mfm_by_focal_list), tot_mfm, repo_exists, error_finding_java_files)` ([`extract_classes_info_d4j.py:317-328`](extract_classes_info_d4j.py:317)).

6.2.28 [`get_class_path()`](extract_classes_info_d4j.py:23) recorre el árbol con `os.walk`, busca un archivo cuyo nombre base coincida y confirma con `path_find.endswith(path_focal_class)`, retornando `None` si no encuentra ninguna ruta ([`extract_classes_info_d4j.py:24-29`](extract_classes_info_d4j.py:24)).

6.2.29 [`parse_focal_methods()`](extract_classes_info_d4j.py:335) invoca [`ClassParser.parse_file()`](ClassParser.py:32) sobre el archivo focal y enriquece la metadata con [`DependencyParserUtils.parse_potential_focal_and_external_dependencies()`](dependency_parser_utils.py:113), la misma función que usa el flujo principal ([`extract_classes_info_d4j.py:339-340`](extract_classes_info_d4j.py:339)).

6.2.30 El filtro de métodos es más restrictivo que en el flujo principal: se conservan solo métodos que no son caso de prueba, no son constructores, no son `abstract` y contienen el modificador `public` ([`extract_classes_info_d4j.py:354-357`](extract_classes_info_d4j.py:354)).

6.2.31 Se copia el diccionario de la clase, se elimina `argument_list`, se agrega la clave `file` y se conservan `fields` y `methods` intactos ([`extract_classes_info_d4j.py:359-364`](extract_classes_info_d4j.py:359)).

6.2.32 Se anida la clase focal en `method['class']` y el método se agrega a la lista de candidatos, sin emparejamiento, sin heurística de invocación única y sin `target` ([`extract_classes_info_d4j.py:365-367`](extract_classes_info_d4j.py:365)).

6.2.33 [`get_mapped_focal_methods()`](extract_classes_info_d4j.py:372) construye por cada método focal un diccionario con `project_name_version`, `focal_class` (la ruta del archivo como cadena) y `focal_method`, y retorna la lista ([`extract_classes_info_d4j.py:374-382`](extract_classes_info_d4j.py:374)).

6.2.34 [`export_mfm()`](extract_classes_info_d4j.py:385) itera por cada lista y elemento con copia profunda, sustituye `focal_class` por el diccionario extraído con `pop('class')` y poda de cada método de la clase ocho claves: `body`, `class`, `used_private_signatures_of_class`, `used_non_private_signatures_of_class`, `class_private_deps_used`, `class_non_private_deps_used`, `signatures_of_external_dependencies` y `external_dependencies` ([`extract_classes_info_d4j.py:391-405`](extract_classes_info_d4j.py:391)).

6.2.35 El nombre del archivo es `{project_name_version}_{mfm_id}.json`, con identificador incremental por método, y se escribe con [`export()`](extract_classes_info_d4j.py:417), que elimina el archivo previo y serializa con `json.dumps` en UTF-8 sin `indent` ([`extract_classes_info_d4j.py:411-429`](extract_classes_info_d4j.py:411)).

6.2.36 El esquema exportado contiene `project_name_version`, `focal_class` con `class_name`, `superclass`, `interfaces`, `class_signature`, `class_modifier`, `has_constructor`, `fields`, `methods`, `imports`, `package` y `file`, y `focal_method` con las claves de firma más `class_private_deps_used`, `class_non_private_deps_used`, `used_private_signatures_of_class`, `used_non_private_signatures_of_class`, `signatures_of_external_dependencies` y `external_dependencies` ([`dependency_parser_utils.py:158-174`](dependency_parser_utils.py:158), [283-284](dependency_parser_utils.py:283), [`extract_classes_info_d4j.py:364`](extract_classes_info_d4j.py:364)).

6.2.37 No existe `test_class`, `test_case` ni `repository` en este JSON; el consumidor [`build_corpus_d4j.py`](build_corpus_d4j.py:319) lee exactamente `focal_class` y `focal_method` ([`build_corpus_d4j.py:327-332`](build_corpus_d4j.py:327)).

### 6.3 Script build_corpus_d4j.py : transforma cada JSON de la minería Defects4J en las tres representaciones de entrada, sin `target`, y exporta el corpus JSON por proyecto y versión, el corpus plano por proyecto y el árbol `data_by_project_and_version` que consume el paso CSV.

6.3.1 Se importan `argparse`, `copy`, `json`, `os`, `re`, `shutil`, `time`, `tqdm` y [`ParserUtils`](build_corpus_d4j.py:9); `copy` se importa sin uso efectivo ([`build_corpus_d4j.py:1-9`](build_corpus_d4j.py:1)).

6.3.2 La cabecera documenta el árbol de salida `data_by_project_and_version/{Proyecto}/{version}/focal_classes/` y `methods/{i}/`, `json/{Proyecto}/{Proyecto}_{n}_f/` y `raw/{Proyecto}/`; el comentario menciona `all_metadata.json`, pero el código escribe `metadata.json` ([`build_corpus_d4j.py:34-85`](build_corpus_d4j.py:34), [212](build_corpus_d4j.py:212)).

6.3.3 Se declaran cinco listas globales de diagnóstico, sin la lista de errores de `target` que sí existe en el flujo principal ([`build_corpus_d4j.py:12-16`](build_corpus_d4j.py:12)).

6.3.4 [`parse_args()`](build_corpus_d4j.py:625) define diez parámetros: `--input_dataset`, `--input_encoding`, `--project_id`, `--output_corpus` y los seis delimitadores con los mismos valores por defecto que el flujo principal ([`build_corpus_d4j.py:629-691`](build_corpus_d4j.py:629)).

6.3.5 No existen los parámetros `--type_dataset`, `--validate_against_d4j_dataset` ni `--d4j_dataset`, y se retorna `vars(parser.parse_args())` ([`build_corpus_d4j.py:693`](build_corpus_d4j.py:693)).

6.3.6 [`main()`](build_corpus_d4j.py:696) desempaqueta los diez argumentos, fija la lista literal de 17 proyectos e inicializa `projects_paths` según `project_id`, con `raise` de cadena para identificadores desconocidos ([`build_corpus_d4j.py:698-721`](build_corpus_d4j.py:698)).

6.3.7 Se recorre el primer nivel de `input_dataset` con `next(os.walk(...))[1]`, donde cada subcarpeta es una revisión `{Proyecto}_{bugId}_f`, y el proyecto se deriva cortando la revisión por `_` ([`build_corpus_d4j.py:724-731`](build_corpus_d4j.py:724)).

6.3.8 Se invoca [`build_corpus()`](build_corpus_d4j.py:88) por cada proyecto, se acumulan los totales y se reportan los errores de sintaxis de las cinco listas, el total de métodos por proyecto y el tiempo total ([`build_corpus_d4j.py:739-782`](build_corpus_d4j.py:739)).

6.3.9 [`build_corpus()`](build_corpus_d4j.py:88) instancia `ParserUtils(input_encoding)` y toma el total de versiones de `len(list_paths_by_project_id)`, sin recorrer el disco ([`build_corpus_d4j.py:100-104`](build_corpus_d4j.py:100)).

6.3.10 Se crean las tres raíces de salida `{output_corpus}/data_by_project_and_version/{project}`, `{output_corpus}/json/{project}` y `{output_corpus}/raw/{project}` ([`build_corpus_d4j.py:106-113`](build_corpus_d4j.py:106)).

6.3.11 Se inicializan siete listas paralelas: las tres representaciones, imports, paquete, ruta de la clase focal y nombre del método focal ([`build_corpus_d4j.py:115-121`](build_corpus_d4j.py:115)).

6.3.12 Por cada ruta de revisión se obtiene `project_name_version` y la versión numérica con `split("_")[1]`, de modo que el sufijo `_f` se descarta en `data_by_project_and_version` ([`build_corpus_d4j.py:128-130`](build_corpus_d4j.py:128)).

6.3.13 Se crean `focal_classes/` y `methods/` en `data_by_project_and_version/{project}/{version}` y se copian las clases focales exportadas por la minería ([`build_corpus_d4j.py:132-146`](build_corpus_d4j.py:132)).

6.3.14 Se itera sobre los archivos de primer nivel de la revisión procesando solo los `.json`, sin recorrer `focal_classes/` ([`build_corpus_d4j.py:154-159`](build_corpus_d4j.py:154)).

6.3.15 Se invoca [`extract_data_from_mapped_test_case()`](build_corpus_d4j.py:319), que retorna siete valores, y se descarta el registro con `continue` cuando la representación estática es `None`; es el único punto de descarte por filtros y errores de sintaxis ([`build_corpus_d4j.py:161-172`](build_corpus_d4j.py:161)).

6.3.16 Se leen `data['focal_class']` y `data['focal_method']`, sin acceder a `test_class`, `test_case` ni `repository`, y se extraen `path_focal_class` desde `focal_class['file']`, `package_focal_class` desde `focal_class['package']` y `focal_method_name` desde `focal_method['method_name']` ([`build_corpus_d4j.py:327-332`](build_corpus_d4j.py:327)).

6.3.17 Se normaliza el método focal con [`clean_comments_in_code()`](build_corpus_d4j.py:601), los reemplazos de espaciado en torno a `.`, `(`, `)`, `[`, `]` y `){`, y [`fix_type_parameters_inconsistences()`](ParserUtils.py:314) ([`build_corpus_d4j.py:334-336`](build_corpus_d4j.py:334)).

6.3.18 Se retornan siete `None` si [`method_body_is_empty()`](ParserUtils.py:66) resulta verdadero, y se valida sintácticamente el método envolviéndolo en `public class AnyClass { ... }` con `validate_all_errors = True`, registrando el fallo en `list_errors_methods_source` ([`build_corpus_d4j.py:338-351`](build_corpus_d4j.py:338)).

6.3.19 Se delega el ensamblado en [`build_format_corpus()`](build_corpus_d4j.py:375) y se descarta el registro si la representación estática es `None`; los imports se serializan uniendo `focal_class['imports']` con `|` ([`build_corpus_d4j.py:353-370`](build_corpus_d4j.py:353)).

6.3.20 Se retorna `(focal_method_name, src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv, imports_focal_class, package_focal_class, path_focal_class)` ([`build_corpus_d4j.py:372`](build_corpus_d4j.py:372)).

6.3.21 [`build_format_corpus()`](build_corpus_d4j.py:375) es réplica de la del flujo principal, con la misma estructura, los mismos literales de plantilla y la misma secuencia de validaciones ([`build_corpus_d4j.py:386-573`](build_corpus_d4j.py:386)).

6.3.22 La firma de clase se compone con [`build_class_signature()`](build_corpus_d4j.py:577) y se valida de forma tolerante añadiendo `" { }"`; si falla se retorna `(None, None, None)` ([`build_corpus_d4j.py:392-402`](build_corpus_d4j.py:392)).

6.3.23 `src_fm_fc_ms_ff` se ensambla con la plantilla `'{} {{ {} {} {} {} }}'` en el orden firma de clase, declaración del método focal, constructores, métodos no privados y campos no privados, seguido de la normalización de saltos de línea y espaciado ([`build_corpus_d4j.py:410-434`](build_corpus_d4j.py:410)).

6.3.24 Las firmas privadas usadas se componen con los constructores privados, los métodos privados de `class_private_deps_used['methods']` y los campos privados de `class_private_deps_used['fields']` ([`build_corpus_d4j.py:437-448`](build_corpus_d4j.py:437)).

6.3.25 Las firmas no privadas usadas se componen con los constructores no privados, los métodos no privados de `class_non_private_deps_used['methods']` y los campos no privados de `class_non_private_deps_used['fields']` ([`build_corpus_d4j.py:450-461`](build_corpus_d4j.py:450)).

6.3.26 El contexto externo se construye por cada elemento de `focal_method['external_dependencies']`, limpiando la firma externa, eliminando `{`, corrigiendo el cierre de parámetros de tipo y validando de forma tolerante; las firmas internas se validan como interfaz auxiliar y cada bloque se envuelve con las etiquetas de contexto externo ([`build_corpus_d4j.py:464-514`](build_corpus_d4j.py:464)).

6.3.27 Se valida conjuntamente el conjunto de firmas focales y, si falla, se registra en `list_errors_focal_signatures` y se aborta el registro ([`build_corpus_d4j.py:534-543`](build_corpus_d4j.py:534)).

6.3.28 `src_fm_fc_dctx` se compone con la plantilla `'{}{} {{ {} {} {} }}{} {}'` y los argumentos `<FCTX>`, firma de clase, cuerpo del método focal, firmas no privadas usadas, firmas privadas usadas, `</FCTX>` y bloque externo, y `src_fm_fc_dctx_priv` usa la misma plantilla envolviendo las firmas privadas con `<PRIVATE_FCTX>` ([`build_corpus_d4j.py:546-571`](build_corpus_d4j.py:546)).

6.3.29 Se retorna la terna `(src_fm_fc_ms_ff, src_fm_fc_dctx, src_fm_fc_dctx_priv)`, que comparte firma de clase, cuerpo del método focal y bloque externo con las recetas de 3.8.21, con la salvedad de que el cuerpo incluido es siempre un método focal público no abstracto y nunca una pareja test-método ([`build_corpus_d4j.py:573`](build_corpus_d4j.py:573)).

6.3.30 El archivo de corpus se nombra `{project_name_version}_{i}_corpus.json`, con `i` propio de la revisión e incrementado solo para registros aceptados ([`build_corpus_d4j.py:176`](build_corpus_d4j.py:176), [214](build_corpus_d4j.py:214)).

6.3.31 Se construye el diccionario de siete claves `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class`, `package_focal_class`, `path_focal_class` y `focal_method_name`, y se escribe en `json/{project}/{project_name_version}/` ([`build_corpus_d4j.py:179-189`](build_corpus_d4j.py:179)).

6.3.32 El mismo diccionario se escribe como `corpus.json` dentro de `methods/{i}/`, archivo que lee el paso CSV, lo que duplica el contenido en dos rutas ([`build_corpus_d4j.py:191-194`](build_corpus_d4j.py:191), [`build_csv_corpus_d4j.pl:119`](d4j_utils/build_csv_corpus_d4j.pl:119)).

6.3.33 Se escriben siete archivos de texto, uno por campo, en `methods/{i}/`: `src_fm_fc_ms_ff.txt`, `src_fm_fc_dctx.txt`, `src_fm_fc_dctx_priv.txt`, `imports_focal_class.txt`, `package_focal_class.txt`, `path_focal_class.txt` y `focal_method_name.txt` ([`build_corpus_d4j.py:195-201`](build_corpus_d4j.py:195)).

6.3.34 Se copia el JSON original de minería como `metadata.json` dentro de `methods/{i}/`, archivo que conserva el esquema completo y que relee la validación cruzada del corpus principal ([`build_corpus_d4j.py:212`](build_corpus_d4j.py:212), [`build_corpus.py:698-704`](build_corpus.py:698)).

6.3.35 Al terminar todas las revisiones se exporta el corpus plano con [`export_corpus_raw()`](build_corpus_d4j.py:259) y se retorna el número de registros ([`build_corpus_d4j.py:218-233`](build_corpus_d4j.py:218)).

6.3.36 No existe deduplicación en ningún nivel: cada método focal público no abstracto de cada clase explícita genera un registro ([`build_corpus_d4j.py:171-214`](build_corpus_d4j.py:171)).

---

## 7) Scripts utilitarios (fuera del flujo principal, ejecución manual)

Los seis utilitarios comparten tres propiedades: ningún script del repositorio los importa ni los ejecuta, ninguna etapa del pipeline consume sus salidas, y se invocan manualmente en momentos puntuales de la investigación ([`analize_tokens_corpus.py:232`](analize_tokens_corpus.py:232), [`compress_folder.py:61`](compress_folder.py:61), [`validate_d4j_repos.py:49`](validate_d4j_repos.py:49)).

### 7.1 analize_tokens_corpus.py : cuantifica la longitud en tokens de cada representación serializada del corpus para decidir la ventana de contexto del modelo, una vez construido un corpus en formato CSV.

7.1.1 [`parse_args()`](analize_tokens_corpus.py:110) define `--path_all_csv_corpus` con valor por defecto `/defects4j_with_dynamtests/corpus_only_public/csv` y la variante `/DynaMTests_project/corpus/csv` como línea comentada ([`analize_tokens_corpus.py:118-123`](analize_tokens_corpus.py:118)).

7.1.2 Se define `--corpus_type` con valor por defecto `all` y dominio esperado `train`, `validation`, `test` o `all`; no se valida el dominio, por lo que un valor distinto de `all` se usa literalmente como nombre de archivo ([`analize_tokens_corpus.py:125-129`](analize_tokens_corpus.py:125)).

7.1.3 Se define `--analyzing_d4j_corpus` con `type=lambda x: bool(strtobool(x))` y valor por defecto `True`, de modo que la cadena `False` sí se convierte en falso ([`analize_tokens_corpus.py:131-135`](analize_tokens_corpus.py:131)).

7.1.4 Se definen `--output_file` con valor por defecto `/defects4j_with_dynamtests/corpus_only_public/corpus_token_analysis.json`, `--encoding` y `--model_base`/`--cacheDirHuggingFace` ([`analize_tokens_corpus.py:137-160`](analize_tokens_corpus.py:137)).

7.1.5 `--encoding` se declara y se lee, pero nunca se aplica, porque `pd.read_csv` se invoca sin `encoding` ([`analize_tokens_corpus.py:27`](analize_tokens_corpus.py:27), [170](analize_tokens_corpus.py:170)).

7.1.6 Los nombres de archivo esperados son `<Proyecto>_methods.csv` con `analyzing_d4j_corpus = True` y `<split>.csv` en caso contrario ([`analize_tokens_corpus.py:23-24`](analize_tokens_corpus.py:23)).

7.1.7 Las columnas requeridas por fila son `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx` y `src_fm_fc_dctx_priv` ([`analize_tokens_corpus.py:33-39`](analize_tokens_corpus.py:33), [57-61](analize_tokens_corpus.py:57)).

7.1.8 [`analize_count_tokens()`](analize_tokens_corpus.py:22) lee el CSV completo con `pandas`, sustituye `pd.NA` por `None`, materializa todas las filas con `df.to_dict(orient='records')` y eleva el límite por campo con `csv.field_size_limit(10**6)` ([`analize_tokens_corpus.py:14`](analize_tokens_corpus.py:14), [27-30](analize_tokens_corpus.py:27)).

7.1.9 Se inicializa un contador por representación con los cuatro intervalos `less_than_or_equal_512`, `in_range_512_and_1024`, `in_range_1024_and_2048` y `greater_than_2048` ([`analize_tokens_corpus.py:41-53`](analize_tokens_corpus.py:41)).

7.1.10 En modo corpus principal se tokeniza también `target`; en modo Defects4J `target` se omite y al final se elimina la clave del resultado ([`analize_tokens_corpus.py:56-71`](analize_tokens_corpus.py:56)).

7.1.11 [`analize_using_tokenizer()`](analize_tokens_corpus.py:76) tokeniza cada representación con `add_special_tokens=False` y `return_attention_mask=False`, y clasifica la longitud en uno de los cuatro intervalos con límites `<= 512`, `(512, 1024]`, `(1024, 2048]` y `> 2048` ([`analize_tokens_corpus.py:77-93`](analize_tokens_corpus.py:77)).

7.1.12 No se aplica `padding`, `truncation` ni `max_length` en la llamada; la asignación `tokenizer.model_max_length = 1024` solo modifica el atributo y no recorta las secuencias medidas ([`analize_tokens_corpus.py:176-177`](analize_tokens_corpus.py:176)).

7.1.13 No se calculan percentiles ni cuantiles: el equivalente funcional es el histograma acumulado de cuatro intervalos ([`analize_tokens_corpus.py:82-93`](analize_tokens_corpus.py:82)).

7.1.14 Cada tokenización hace `copy.deepcopy` del diccionario de conteos, por lo que el utilitario resulta intensivo en tiempo y en memoria ([`analize_tokens_corpus.py:95`](analize_tokens_corpus.py:95)).

7.1.15 El tokenizador requerido es `Salesforce/codet5p-220m`, cargado con `AutoTokenizer.from_pretrained(model_base, cache_dir=cache_dir_hf)` ([`analize_tokens_corpus.py:152`](analize_tokens_corpus.py:152), [175](analize_tokens_corpus.py:175)).

7.1.16 La salida es un único JSON en `--output_file` escrito con `indent=4` y borrando el archivo previo, con clave por corpus procesado, `total_rows` y `counts_by_input_type` ([`analize_tokens_corpus.py:98-107`](analize_tokens_corpus.py:98), [195-198](analize_tokens_corpus.py:195), [227](analize_tokens_corpus.py:227)).

7.1.17 No hay manejo de errores: un CSV inexistente produce `FileNotFoundError` de `pandas`, una columna faltante produce `KeyError` y una carpeta de salida inexistente produce `FileNotFoundError` al escribir ([`analize_tokens_corpus.py:59-61`](analize_tokens_corpus.py:59), [105](analize_tokens_corpus.py:105)).

### 7.2 compress_folder.py : empaqueta una carpeta o un archivo en un `.tar.bz2` para transportar o archivar artefactos del corpus.

7.2.1 [`parse_args()`](compress_folder.py:36) define `--input_folder_path` y `--output_path`, ambos sin valor por defecto, y `--type_input` con valor por defecto `folder` ([`compress_folder.py:41-56`](compress_folder.py:41)).

7.2.2 Cualquier valor de `--type_input` distinto de `folder` activa el modo de archivo único ([`compress_folder.py:51-56`](compress_folder.py:51), [69-72](compress_folder.py:69)).

7.2.3 [`main()`](compress_folder.py:61) lee los tres parámetros y delega en [`compress_folder_to_tar_bz2()`](compress_folder.py:18) o [`compress_file_to_tar_bz2()`](compress_folder.py:6) según `type_input` ([`compress_folder.py:62-72`](compress_folder.py:62)).

7.2.4 La compresión se realiza con `tarfile.open(output_path, "w:bz2")` y una única llamada a `tar.add()`, con `arcname` igual al nombre base de la ruta recibida ([`compress_folder.py:12-14`](compress_folder.py:12), [24-26](compress_folder.py:24)).

7.2.5 El formato generado es exclusivamente `.tar.bz2`, sin soporte para otros formatos ni niveles de compresión configurables ([`compress_folder.py:12`](compress_folder.py:12)).

7.2.6 La apertura en modo `"w:bz2"` trunca el archivo de salida si ya existe, sin comprobación previa ni advertencia, y no se crean los directorios intermedios de `output_path` ([`compress_folder.py:12`](compress_folder.py:12)).

7.2.7 Se lanza `FileNotFoundError` explícito si la ruta de entrada no existe o no es del tipo esperado ([`compress_folder.py:8-9`](compress_folder.py:8), [20-21](compress_folder.py:20)).

### 7.3 get_repos_not_exists.py : extrae los identificadores de repositorio que fallaron con el motivo de repositorio inexistente y los escribe en un archivo de texto para habilitar un reintento selectivo.

7.3.1 No existe `parse_args()` ni bloque `__main__`: la lógica se ejecuta en el nivel de módulo al importarse o ejecutarse ([`get_repos_not_exists.py:22-36`](get_repos_not_exists.py:22)).

7.3.2 [`list_carpetas()`](get_repos_not_exists.py:4) recibe una ruta y devuelve un `set` con los nombres de los elementos que son directorios ([`get_repos_not_exists.py:10-19`](get_repos_not_exists.py:10)).

7.3.3 La ruta está fijada en el código como `/root/mining_results/train/output_empty/1_repo_not_exists` y solo se inspecciona la partición `train` ([`get_repos_not_exists.py:22`](get_repos_not_exists.py:22)).

7.3.4 El conjunto de carpetas se acumula en `carpetas` desde la única fuente `outs_not_exists`, se ordena y se convierte en lista ([`get_repos_not_exists.py:24-30`](get_repos_not_exists.py:24)).

7.3.5 Cada nombre de carpeta, es decir cada `repo_id`, se escribe en una línea de `/root/repos_not_exists.txt` con modo `'w'`, truncando silenciosamente el archivo previo ([`get_repos_not_exists.py:32-34`](get_repos_not_exists.py:32)).

7.3.6 El archivo `/root/repos_not_exists.txt` es consumido por [`get_repos_not_exists()`](find_map_tests_cases_from_repo.py:733) dentro del minero, pero su llamada en [`analyze_repositories()`](find_map_tests_cases_from_repo.py:745) está comentada, de modo que el modo reintento exige descomentar tres líneas manualmente ([`find_map_tests_cases_from_repo.py:760-766`](find_map_tests_cases_from_repo.py:760)).

7.3.7 Si la ruta de entrada no existe, `os.listdir` lanza `FileNotFoundError` sin captura y el script termina sin escribir salida ([`get_repos_not_exists.py:24`](get_repos_not_exists.py:24)).

### 7.4 validate_d4j_in_CodeSearchNet.py : audita la fuga de datos verificando si los repositorios y métodos focales del corpus Defects4J aparecen en los corpus públicos CodeSearchNet y `codeparrot/github-code`.

7.4.1 No existe `parse_args()` ni bloque `main`: todo el flujo se ejecuta en el nivel de módulo y las rutas son constantes en el código ([`validate_d4j_in_CodeSearchNet.py:117-336`](validate_d4j_in_CodeSearchNet.py:117)).

7.4.2 Se declara el mapa proyecto Defects4J → identificador de repositorio GitHub para los 17 proyectos ([`validate_d4j_in_CodeSearchNet.py:19-37`](validate_d4j_in_CodeSearchNet.py:19)).

7.4.3 El corpus de evaluación se lee en `/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version` con [`get_focal_methods_by_d4j_project()`](validate_d4j_in_CodeSearchNet.py:54), que recorre `<proyecto>/<version>/methods/<metodo>/metadata.json` y extrae `focal_method.body` y `focal_class.file` ([`validate_d4j_in_CodeSearchNet.py:68-88`](validate_d4j_in_CodeSearchNet.py:68), [138](validate_d4j_in_CodeSearchNet.py:138)).

7.4.4 Se descarga CodeSearchNet con `load_dataset('irds/codesearchnet', 'docs', cache_dir='/CodeSearchNet/dataset')`, filtrado a `language == "java"` ([`validate_d4j_in_CodeSearchNet.py:124-126`](validate_d4j_in_CodeSearchNet.py:124)).

7.4.5 Se transmite `codeparrot/github-code` en modo `streaming=True` con `split="train"` y caché en `/CodeParrot_GithubCode/dataset` ([`validate_d4j_in_CodeSearchNet.py:218-228`](validate_d4j_in_CodeSearchNet.py:218)).

7.4.6 La normalización se aplica a ambos lados: [`clean_comments_in_code()`](validate_d4j_in_CodeSearchNet.py:48) elimina comentarios y colapsa saltos, tabulaciones y espacios, y después se aplican sustituciones de espaciado alrededor de `.`, `){`, `(`, `)` y `[`/`]` ([`validate_d4j_in_CodeSearchNet.py:40-48`](validate_d4j_in_CodeSearchNet.py:40), [82](validate_d4j_in_CodeSearchNet.py:82), [287](validate_d4j_in_CodeSearchNet.py:287)).

7.4.7 La validación en CodeSearchNet es a nivel de repositorio: se construye el mapa inverso repositorio→proyecto y se cuenta la pertenencia de los 17 repositorios al split de documentación Java ([`validate_d4j_in_CodeSearchNet.py:131-133`](validate_d4j_in_CodeSearchNet.py:131), [155-170](validate_d4j_in_CodeSearchNet.py:155)).

7.4.8 El filtro del subconjunto de GitHub exige `language == "Java"`, licencia dentro de la lista usada por CodeT5+, `repo_name` perteneciente a un proyecto Defects4J y `path` dentro del conjunto de rutas de clases focales del corpus de evaluación ([`validate_d4j_in_CodeSearchNet.py:233-241`](validate_d4j_in_CodeSearchNet.py:233)).

7.4.9 Se descartan los archivos con menos de 50 o más de 2000 tokens, replicando el criterio declarado de CodeT5+ ([`validate_d4j_in_CodeSearchNet.py:274-279`](validate_d4j_in_CodeSearchNet.py:274)).

7.4.10 Los cuerpos de método del archivo se extraen con [`get_body_methods_from_class()`](ParserUtils.py:361) y se comparan contra el conjunto normalizado de cuerpos focales del proyecto ([`validate_d4j_in_CodeSearchNet.py:292`](validate_d4j_in_CodeSearchNet.py:292), [298-310](validate_d4j_in_CodeSearchNet.py:298)).

7.4.11 La salida es un JSON por proyecto en `/CodeParrot_GithubCode/<Proyecto>.json` con los ítems que contienen un cuerpo focal y la clave adicional `focal_method_existing_in_d4j`, además de recuentos por `stdout` ([`validate_d4j_in_CodeSearchNet.py:304-305`](validate_d4j_in_CodeSearchNet.py:304), [326-332](validate_d4j_in_CodeSearchNet.py:326)).

7.4.12 La condición de acumulación consulta un diccionario que nunca se llena porque el bloque que lo llenaba está comentado, de modo que la lista del proyecto se reinicia en cada coincidencia y solo se conserva el último hallazgo ([`validate_d4j_in_CodeSearchNet.py:307`](validate_d4j_in_CodeSearchNet.py:307), [310](validate_d4j_in_CodeSearchNet.py:310), [178-188](validate_d4j_in_CodeSearchNet.py:178)).

7.4.13 `record['repo'].lower()` se evalúa sin comprobación de nulo, por lo que un registro con `repo` ausente aborta el recorrido de CodeSearchNet ([`validate_d4j_in_CodeSearchNet.py:159`](validate_d4j_in_CodeSearchNet.py:159)).

### 7.5 validate_d4j_in_GithubCode.py : a partir de los hallazgos JSON del script anterior, identifica en qué versiones del corpus Defects4J y en qué carpetas de método se materializa cada método focal encontrado en código público.

7.5.1 No existe `parse_args()` ni bloque `main`: la lógica se ejecuta en el nivel de módulo ([`validate_d4j_in_GithubCode.py:144-184`](validate_d4j_in_GithubCode.py:144)).

7.5.2 Se leen los hallazgos por proyecto en `/CodeParrot_GithubCode/<Proyecto>.json` para el subconjunto fijo `["Cli", "Compress", "JacksonCore", "JacksonDatabind"]` ([`validate_d4j_in_GithubCode.py:152-158`](validate_d4j_in_GithubCode.py:152)).

7.5.3 Se construye el índice de hallazgos como diccionario ruta de clase focal → conjunto de cuerpos focales normalizados, tomados de la clave `focal_method_existing_in_d4j` ([`validate_d4j_in_GithubCode.py:150-171`](validate_d4j_in_GithubCode.py:150), [163-168](validate_d4j_in_GithubCode.py:163)).

7.5.4 Se recorre el corpus de evaluación en `/defects4j_with_dynamtests/corpus_only_public/data_by_project_and_version` con la misma normalización, extrayendo `focal_class.file` y `focal_method.body` ([`validate_d4j_in_GithubCode.py:87-92`](validate_d4j_in_GithubCode.py:87), [146](validate_d4j_in_GithubCode.py:146)).

7.5.5 El cruce registra proyecto y versión más la carpeta de método cuando coinciden la ruta de la clase focal y el cuerpo normalizado; si la ruta no está en el índice el método se descarta ([`validate_d4j_in_GithubCode.py:98-113`](validate_d4j_in_GithubCode.py:98)).

7.5.6 Solo se protege la lectura del archivo con `os.path.exists`; `findings_by_d4j_project[d4j_project]` se indexa directamente, por lo que un JSON ausente produce `KeyError` ([`validate_d4j_in_GithubCode.py:70`](validate_d4j_in_GithubCode.py:70), [156](validate_d4j_in_GithubCode.py:156)).

7.5.7 La salida es solo `stdout`: total de clases focales procesadas y, por proyecto y versión, el conjunto de carpetas de método coincidentes ([`validate_d4j_in_GithubCode.py:178-184`](validate_d4j_in_GithubCode.py:178)).

### 7.6 validate_d4j_repos.py : comprueba si los identificadores numéricos de repositorio GitHub de los 17 proyectos Defects4J están presentes en el árbol de salida de la minería.

7.6.1 No existe `parse_args()` ni bloque `main`: la ejecución es de nivel de módulo ([`validate_d4j_repos.py:49-55`](validate_d4j_repos.py:49)).

7.6.2 Se declara `DEFECTS4J_PROJECTS_BY_REPO_ID` con los 17 identificadores numéricos y su descripción `Proyecto -> URL` ([`validate_d4j_repos.py:9-27`](validate_d4j_repos.py:9)).

7.6.3 [`get_total_repos()`](validate_d4j_repos.py:29) recorre los elementos de primer nivel de la ruta, conserva solo los directorios y convierte el nombre a entero ([`validate_d4j_repos.py:29-46`](validate_d4j_repos.py:29)).

7.6.4 La ruta está fijada con separadores Windows como `E:/000_Tesis/DynaMTests/mining_results/train/output`, de modo que solo se inspecciona la partición `train` y la carpeta `output` ([`validate_d4j_repos.py:49`](validate_d4j_repos.py:49)).

7.6.5 Para cada `repo_id` presente en el diccionario se imprime `Si existe el repo: {repo_id}`, criterio que no distingue entre proyecto minado con casos y proyecto minado sin casos ([`validate_d4j_repos.py:53-55`](validate_d4j_repos.py:53)).

7.6.6 `int(elemento)` sobre nombres de directorio no numéricos lanza `ValueError` sin captura, y un directorio auxiliar dentro de `output` rompe la ejecución ([`validate_d4j_repos.py:40`](validate_d4j_repos.py:40)).

7.6.7 Los proyectos del diccionario que no aparecen en el árbol simplemente no se imprimen, sin resumen negativo explícito ([`validate_d4j_repos.py:55`](validate_d4j_repos.py:55)).

---

## Contrato de datos entre etapas

El pipeline principal encadena tres formatos JSON y un CSV: JSON de minería → JSON de dataset (copia byte a byte) → JSON de corpus → CSV. El flujo Defects4J sustituye la etapa de depuración por una selección explícita de revisiones y añade el árbol `data_by_project_and_version` como insumo del ensamblado CSV en Perl.

| Etapa | Entrada | Clave de agrupación | Transformación | Salida |
|---|---|---|---|---|
| 1 (minería) | Repositorios GitHub clonados | Par test ↔ método focal | Extracción AST y enriquecimiento de contexto dinámico | `{output}/{repo_id}/{repo_id}_{mtc_id}.json` |
| 2 (dataset) | `{mining_input}/{split}/output/{repo_id}/*.json` | `focal_method.body + test_case.body` sin separador; conjuntos compartidos train > validation > test | Filtro Defects4J por URL, filtro de cuerpos nulos, dedup por par y copia byte a byte | `{output_dataset}/{split}/{repo_id}/*.json` |
| 3 (corpus) | `{input_dataset}/{repo_id}/*.json` | `body_method + target` normalizados, por invocación | Limpieza, validación sintáctica, filtros, cruce Defects4J por cuerpo focal y ensamblado de tres representaciones | `{output_corpus}/json/{split}/{repo_id}/*_corpus.json` y `{output_corpus}/raw/{split}/*.txt` |
| 4 (CSV) | `{corpus_json}/{split}/{repo_id}/*_corpus.json` | Ninguna | Consolidación en `DataFrame` y mezcla con `random_state=42` | `{corpus_csv}/{split}.csv` |

**Etapa 1 → etapa 2 (campo por campo).** La estructura de entrada es `{mining_input}/{split}/output/{repo_id}/{repo_id}_{mtc_id}.json`, un archivo por par mapeado ([`clean_duplicates_and_build_dataset.py:143-145`](clean_duplicates_and_build_dataset.py:143)). Los campos efectivamente leídos son `test_case.body`, `focal_method.body` y `repository.url` ([`clean_duplicates_and_build_dataset.py:93-97`](clean_duplicates_and_build_dataset.py:93)). Los bloques que deben existir para no abortar son `test_case`, `focal_method` y `repository` ([`clean_duplicates_and_build_dataset.py:93-97`](clean_duplicates_and_build_dataset.py:93)). El esquema de salida no cambia: la copia es byte a byte y no hay campos añadidos, eliminados ni renombrados ([`clean_duplicates_and_build_dataset.py:128-132`](clean_duplicates_and_build_dataset.py:128)).

**Etapa 2 → etapa 3 (campo por campo).** `test_class` aporta `imports` ([`build_corpus.py:407`](build_corpus.py:407)); `test_case` aporta `body` como semilla del `target` y `modifiers` para el filtro `@Ignore` ([`build_corpus.py:349-352`](build_corpus.py:349)); `focal_class` aporta `class_signature`, `class_name`, `superclass`, `interfaces`, `methods` con `full_signature`, `modifiers` e `is_constructor`, `fields` con `original_string` y `modifier`, e `imports` ([`build_corpus.py:342`](build_corpus.py:342), [448-466](build_corpus.py:448), [632-634](build_corpus.py:632)); `focal_method` aporta `modifiers`, `body`, `class_private_deps_used` y `class_non_private_deps_used` con subclaves `methods` y `fields`, y `external_dependencies` con `class_signature`, `fields` y `methods` ([`build_corpus.py:346-356`](build_corpus.py:346), [481-500](build_corpus.py:481), [518-541](build_corpus.py:518)). No se consumen `focal_class.class_modifier`, `has_constructor`, `package`, `file`, ni prácticamente ningún campo del caso de prueba salvo `body` y `modifiers` ([`build_corpus.py:342-356`](build_corpus.py:342)).

**Etapa 3 → etapa 4 (las seis claves del corpus).** El registro JSON de corpus contiene, en este orden, `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class` e `imports_test_class`, todas de tipo cadena ([`build_corpus.py:178-185`](build_corpus.py:178)). El CSV replica esas seis columnas en el mismo orden, con encabezado y sin índice ([`convert_json_corpus_to_csv_input.py:27`](convert_json_corpus_to_csv_input.py:27), [114](convert_json_corpus_to_csv_input.py:114)).

**Corpus plano del flujo principal (seis archivos).** Se escriben `input_methods_src_fm_fc_ms_ff.txt`, `input_methods_src_fm_fc_dctx.txt`, `input_methods_src_fm_fc_dctx_priv.txt`, `output_tests.txt`, `imports_focal_class.txt` e `imports_test_class.txt`, alineados por índice y con una línea por registro ([`build_corpus.py:284-325`](build_corpus.py:284)).

**Corpus de evaluación Defects4J (siete claves y quince columnas).** El JSON de corpus de evaluación contiene `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class`, `package_focal_class`, `path_focal_class` y `focal_method_name`, sin `target` ([`build_corpus_d4j.py:179-187`](build_corpus_d4j.py:179)). El corpus plano emite esos siete campos como siete archivos por proyecto ([`build_corpus_d4j.py:195-201`](build_corpus_d4j.py:195), [259-316](build_corpus_d4j.py:259)). El CSV final amplía a quince columnas: `id`, `project`, `version`, `number_method_by_version`, `modified_class`, `focal_method`, `focal_class`, `path_focal_class_in_project`, `test_class`, `path_test_class`, `package_focal_class`, `imports_focal_class`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx` y `src_fm_fc_dctx_priv` ([`build_csv_corpus_d4j.pl:242-259`](d4j_utils/build_csv_corpus_d4j.pl:242)).

**Trazabilidad y puntos de pérdida.** La etapa 2 conserva el identificador de repositorio solo por el nombre de la carpeta, la etapa 3 lo conserva igual y la etapa 4 lo pierde por completo en el CSV ([`convert_json_corpus_to_csv_input.py:114`](convert_json_corpus_to_csv_input.py:114)). El identificador del par mapeado sobrevive en el nombre del JSON de la etapa 3 y desaparece en el corpus plano y en el CSV ([`build_corpus.py:174-176`](build_corpus.py:174)). Ninguno de los tres formatos declara versión ni esquema, por lo que un cambio de claves en la etapa 3 no es detectable por la etapa 4 ([`build_corpus.py:178-185`](build_corpus.py:178)). Los descartes no se materializan en ningún artefacto persistente: las seis listas de error viven en memoria y los contadores de la etapa 2 se imprimen por consola ([`build_corpus.py:40-45`](build_corpus.py:40), [`clean_duplicates_and_build_dataset.py:165-169`](clean_duplicates_and_build_dataset.py:165)).

---

## Diferencias entre el corpus de entrenamiento y el corpus de evaluación Defects4J

| Aspecto | Flujo principal (entrenamiento) | Flujo Defects4J (evaluación) |
|---|---|---|
| Obtención del código | Clonado superficial desde GitHub con `git.Repo.clone_from` ([`find_map_tests_cases_from_repo.py:82-86`](find_map_tests_cases_from_repo.py:82)) | `defects4j checkout` de la versión fija y compilación ([`d4j_utils/export_revisions.sh:22-23`](d4j_utils/export_revisions.sh:22)) |
| Selección de clases | Todas las clases menos las de test, por diferencia de conjuntos ([`find_map_tests_cases_from_repo.py:274-276`](find_map_tests_cases_from_repo.py:274)) | Lista explícita de clases modificadas por bug ([`d4j_utils/export_focal_classes.sh:14-23`](d4j_utils/export_focal_classes.sh:14)) |
| Trazabilidad test ↔ focal | [`match_test_cases()`](find_map_tests_cases_from_repo.py:581) con coincidencia por nombre e invocación única | Inexistente: cada método público no abstracto es un registro ([`extract_classes_info_d4j.py:354-367`](extract_classes_info_d4j.py:354)) |
| Filtros de métodos | Constructores admitidos (filtro comentado), sin condición de visibilidad ([`find_map_tests_cases_from_repo.py:565`](find_map_tests_cases_from_repo.py:565)) | Constructores excluidos y modificador `public` exigido ([`extract_classes_info_d4j.py:354-357`](extract_classes_info_d4j.py:354)) |
| Depuración y particiones | Dedup por par, exclusión por URL Defects4J y estructura `dataset/{split}/{repo_id}` ([`clean_duplicates_and_build_dataset.py:142`](clean_duplicates_and_build_dataset.py:142)) | No existe etapa equivalente ni noción de split ([`build_corpus_d4j.py:158`](build_corpus_d4j.py:158)) |
| Claves del JSON de corpus | `target`, `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class`, `imports_test_class` ([`build_corpus.py:178-185`](build_corpus.py:178)) | `src_fm_fc_ms_ff`, `src_fm_fc_dctx`, `src_fm_fc_dctx_priv`, `imports_focal_class`, `package_focal_class`, `path_focal_class`, `focal_method_name` ([`build_corpus_d4j.py:179-187`](build_corpus_d4j.py:179)) |
| Validación de fuga | [`get_focal_methods_by_d4j_project()`](build_corpus.py:680) indexa cuerpos del benchmark y omite coincidencias ([`build_corpus.py:154-164`](build_corpus.py:154)) | No aplica: el corpus evaluado es el propio benchmark ([`build_corpus_d4j.py:757-770`](build_corpus_d4j.py:757)) |
| Deduplicación | Por par `body_method + target` en `unique_sources_targets` ([`build_corpus.py:166-170`](build_corpus.py:166)) | Ninguna en ningún nivel ([`build_corpus_d4j.py:171-214`](build_corpus_d4j.py:171)) |
| Conversión a CSV | `pandas`, seis columnas, mezcla con `SEED = 42` ([`convert_json_corpus_to_csv_input.py:109-114`](convert_json_corpus_to_csv_input.py:109)) | `Text::CSV`, quince columnas, ordenadas por versión y número de método ([`build_csv_corpus_d4j.pl:227-259`](d4j_utils/build_csv_corpus_d4j.pl:227)) |
| Función del artefacto | Entrenamiento supervisado sequence-to-sequence | Generación y ejecución de tests sobre el framework Defects4J, sin `target` ([`DEFECTS4J_README.md:3-5`](DEFECTS4J_README.md:3)) |

---

## Riesgos y puntos de mejora detectados

1. **Emparejamiento por nombre con sobrecargas.** [`match_test_cases()`](find_map_tests_cases_from_repo.py:581) usa `list.index()` sobre nombres normalizados, por lo que ante sobrecargas del mismo nombre se selecciona siempre el primer método focal, sin verificar aridad ni tipos ([`find_map_tests_cases_from_repo.py:612-615`](find_map_tests_cases_from_repo.py:612)).

2. **Mapeo de archivos dependiente de la convención Maven.** La correspondencia Clase de Prueba → Clase Focal depende de la sustitución literal de `/src/test/` por `/src/main/` y del recorte de `test`, y usa `.index()` sobre la lista de rutas normalizadas ([`find_map_tests_cases_from_repo.py:289-305`](find_map_tests_cases_from_repo.py:289)).

3. **Clave de deduplicación sin delimitador.** La etapa 2 concatena `focal_method.body + test_case.body` y la etapa 3 concatena `src_only_method_body + target`, ambas sin separador, de modo que el criterio no es inyectivo; el impacto efectivo es ínfimo según el análisis de la sección de referencia (a confirmar empíricamente) ([`clean_duplicates_and_build_dataset.py:103`](clean_duplicates_and_build_dataset.py:103), [`build_corpus.py:166-170`](build_corpus.py:166)).

4. **Tipo de `bool` en `argparse`.** `--validate_against_d4j_dataset` y `--extract_only_focal_classes` se declaran con `type=bool`, por lo que cualquier cadena no vacía —incluido `False`— produce `True` y solo la cadena vacía produce `False` ([`build_corpus.py:743-745`](build_corpus.py:743), [`extract_classes_info_d4j.py:505-511`](extract_classes_info_d4j.py:505)).

5. **Ausencia total de truncamiento.** No existe límite de longitud ni de tokens en ninguna representación, ni cota al número de bloques `<ECTX>`; el control de longitud queda delegado al tokenizador del modelo ([`build_corpus.py:416`](build_corpus.py:416), [519-563](build_corpus.py:519), [`build_corpus_d4j.py:464-514`](build_corpus_d4j.py:464)).

6. **Duplicación de utilidades AST en tres archivos.** `ClassParser`, `DependencyClassParser` y `ParserUtils` mantienen copias independientes de `match_from_span`, `traverse_type`, `children_of_type` y `get_class_full_signature`, de modo que cualquier corrección debe replicarse en tres lugares ([`ClassParser.py:1678-1745`](ClassParser.py:1678), [`DependencyClassParser.py:362-428`](DependencyClassParser.py:362), [`ParserUtils.py:397-444`](ParserUtils.py:397)).

7. **Duplicación de la lógica de corpus.** `build_format_corpus()`, `build_class_signature()`, `clean_comments_in_code()`, `clean_tabs_and_new_lines()` y los dos envoltorios de anotaciones están copiados literalmente entre los dos constructores de corpus, sin importación entre módulos ([`build_corpus.py:416`](build_corpus.py:416), [`build_corpus_d4j.py:375`](build_corpus_d4j.py:375)).

8. **Rutas codificadas de forma rígida.** Los valores por defecto y las rutas internas apuntan a entornos concretos: `/root/repos_not_exists.txt` ([`find_map_tests_cases_from_repo.py:736`](find_map_tests_cases_from_repo.py:736)), rutas `E:/000_Tesis/...` en los scripts de dataset y corpus ([`clean_duplicates_and_build_dataset.py:177-189`](clean_duplicates_and_build_dataset.py:177), [`build_corpus_d4j.py:630-655`](build_corpus_d4j.py:630)) y rutas absolutas en los utilitarios ([`get_repos_not_exists.py:22`](get_repos_not_exists.py:22), [`validate_d4j_repos.py:49`](validate_d4j_repos.py:49)).

9. **Candidatos de migración a Spoon.** La resolución manual de tipos y sobrecargas en [`get_method_m_deps()`](ClassParser.py:923), [`get_method_m_refs_deps()`](ClassParser.py:1168) y [`get_method_f_deps()`](ClassParser.py:1278), junto con las heurísticas de `unknownType` de [`get_methods_from_external_dependency()`](dependency_parser_utils.py:560), corresponde a información que un modelo de programa resolvería con type binding; los puntos de pérdida son la resolución de receptores no declarados, la imposibilidad de inferir tipos en cadenas de campos anidados y el descarte de `var` de Java 11 ([`ClassParser.py:1059-1109`](ClassParser.py:1059), [1327-1331](ClassParser.py:1327), [1415-1417](ClassParser.py:1415)).

10. **Coincidencia parcial por `unknownType`.** Los parámetros no resolubles se etiquetan como `unknownType` y se aceptan como coincidencia parcial, lo que puede asociar una invocación a la sobrecarga equivocada cuando varias sobrecargas difieren solo en tipos no inferibles ([`ClassParser.py:1629`](ClassParser.py:1629), [`dependency_parser_utils.py:653-655`](dependency_parser_utils.py:653)).

11. **Dependencia de `grep` con `shell=True`.** La detección de clases de prueba y de archivos Java depende de un binario Unix, pese a las adaptaciones explícitas para Windows en el manejo de rutas ([`find_map_tests_cases_from_repo.py:220`](find_map_tests_cases_from_repo.py:220), [257](find_map_tests_cases_from_repo.py:257), [`extract_classes_info_d4j.py:133`](extract_classes_info_d4j.py:133)).

12. **Descarte silencioso y no auditable.** Doce condiciones distintas descartan el registro con `continue` en la etapa 3 y seis en la etapa de evaluación, sin registrar el motivo; los motivos solo son reconstruibles por las longitudes de las listas de error en memoria, que no se exportan ([`build_corpus.py:151-152`](build_corpus.py:151), [`build_corpus_d4j.py:171-172`](build_corpus_d4j.py:171)).

13. **Constructores como métodos focales en entrenamiento.** El filtro está comentado en el minero de entrenamiento, mientras el de evaluación los excluye siempre, por lo que las distribuciones de entrada de ambos corpus no son estrictamente comparables ([`find_map_tests_cases_from_repo.py:565`](find_map_tests_cases_from_repo.py:565), [`extract_classes_info_d4j.py:355`](extract_classes_info_d4j.py:355)).

14. **Inconsistencia de encoding.** La etapa 2 lee el JSON con el encoding por defecto del sistema, la etapa 3 permite `utf-8` o `cp1252` y la etapa 4 declara `--input_encoding` sin aplicarlo, porque `pd.read_json` decide el encoding por su cuenta ([`clean_duplicates_and_build_dataset.py:90`](clean_duplicates_and_build_dataset.py:90), [`build_corpus.py:729-735`](build_corpus.py:729), [`convert_json_corpus_to_csv_input.py:58`](convert_json_corpus_to_csv_input.py:58)).

15. **Reproducibilidad del orden del CSV.** `os.listdir` devuelve un orden dependiente del sistema de archivos y `sample` con semilla fija aplica una permutación sobre esa secuencia, por lo que la semilla solo garantiza reproducibilidad dentro del mismo orden de entrada ([`convert_json_corpus_to_csv_input.py:109-110`](convert_json_corpus_to_csv_input.py:109)).

16. **Inferencia de tipos en `pandas`.** `pd.read_json` infiere tipos por valor, de modo que celdas que parezcan numéricas o booleanas pueden dejar de ser cadenas y alterar el esquema respecto del JSON original ([`convert_json_corpus_to_csv_input.py:57-59`](convert_json_corpus_to_csv_input.py:57)).

17. **`raise` con literales de cadena.** Los identificadores de proyecto inválidos y las entradas inexistentes se manejan con `raise` de cadena, que en Python 3 produce `TypeError` en lugar de un mensaje de error controlado ([`extract_classes_info_d4j.py:544`](extract_classes_info_d4j.py:544), [568](extract_classes_info_d4j.py:568), [`build_corpus_d4j.py:721`](build_corpus_d4j.py:721)).

18. **Dependencias no declaradas del flujo Defects4J.** Los envoltorios requieren `jq` y los módulos Perl `JSON` y `Text::CSV`, además de las bibliotecas internas del framework, y ninguna de ellas figura en el listado de dependencias del README ([`export_focal_classes.sh:20`](d4j_utils/export_focal_classes.sh:20), [`build_csv_corpus_d4j.pl:10-17`](d4j_utils/build_csv_corpus_d4j.pl:10), [`DEFECTS4J_README.md:45`](DEFECTS4J_README.md:45)).

19. **Pérdida de registros en el CSV de evaluación.** Solo se emiten métodos cuya clase focal figura en `modified_classes/{id}.src`, por lo que el corpus JSON y el CSV no tienen el mismo número de registros ([`build_csv_corpus_d4j.pl:80-85`](d4j_utils/build_csv_corpus_d4j.pl:80), [141](d4j_utils/build_csv_corpus_d4j.pl:141)).

20. **Correspondencia por nombre simple de clase.** El ensamblado CSV deriva `focal_class_name` del último punto del nombre calificado, y el minero de evaluación localiza clases por subcadena y por sufijo de ruta, lo que puede producir coincidencias inesperadas entre paquetes ([`build_csv_corpus_d4j.pl:141-149`](d4j_utils/build_csv_corpus_d4j.pl:141), [`extract_classes_info_d4j.py:27-29`](extract_classes_info_d4j.py:27), [259](extract_classes_info_d4j.py:259)).

21. **Suposición del formato de revisión.** `project_name_version.split("_")[1]` presupone `{Proyecto}_{bugId}_f` y lanza `IndexError` ante cualquier otro nombre, y el árbol de salida indexa por el identificador numérico, perdiendo el sufijo `_f` ([`build_corpus_d4j.py:130`](build_corpus_d4j.py:130), [132](build_corpus_d4j.py:132)).

22. **Fuga de estado de directorio en el pool.** [`find_focal_classes()`](extract_classes_info_d4j.py:101) ejecuta `os.chdir(root)` sin restaurar el directorio al terminar, y el pool reutiliza procesos entre revisiones ([`extract_classes_info_d4j.py:123`](extract_classes_info_d4j.py:123)).

23. **Fallo que aborta todo el lote.** En la minería de evaluación, cualquier excepción por clase se re-lanza y propaga el fallo al pool, a diferencia del flujo principal, que captura y continúa con el siguiente par ([`extract_classes_info_d4j.py:289-301`](extract_classes_info_d4j.py:289)).

24. **Pérdida de hallazgos en la auditoría de fuga.** La condición de acumulación consulta un diccionario que nunca se llena, por lo que la lista de hallazgos por proyecto se reinicia en cada coincidencia y solo se conserva el último elemento ([`validate_d4j_in_CodeSearchNet.py:307`](validate_d4j_in_CodeSearchNet.py:307), [310](validate_d4j_in_CodeSearchNet.py:310)).

25. **Fragilidad de los utilitarios.** La ruta fija y la conversión `int(elemento)` hacen que cualquier carpeta no numérica rompa [`validate_d4j_repos.py`](validate_d4j_repos.py:29), y la indexación directa del diccionario de hallazgos produce `KeyError` si falta un JSON de proyecto ([`validate_d4j_repos.py:40`](validate_d4j_repos.py:40), [`validate_d4j_in_GithubCode.py:70`](validate_d4j_in_GithubCode.py:70)).

26. **Código declarado y no utilizado.** `DEFECTS4J_PROJECTS_BY_REPO_ID` se declara sin consultarse en la etapa 2, y `get_total_mapped_test_cases()` y `get_total_repos()` de los constructores de corpus están implementados pero no invocados ([`clean_duplicates_and_build_dataset.py:9-27`](clean_duplicates_and_build_dataset.py:9), [`build_corpus.py:64-77`](build_corpus.py:64), [`build_corpus_d4j.py:19`](build_corpus_d4j.py:19)).

27. **Reutilización de nombre de variable con dos tipos.** `tot_mtc` se desempaqueta como tupla y se reutiliza como entero de casos mapeados en el mismo ámbito, lo que vuelve ambigua la lectura de la condición de clasificación ([`find_map_tests_cases_from_repo.py:149-152`](find_map_tests_cases_from_repo.py:149)).
