from DependencyClassParser import DependencyClassParser

# Omitimos en var_declars y external_dependencies las dependencias de tipos de datos de las clases de java.lang
JAVA_LANG_CLASSES_TYPES = [
    "Boolean",
    "boolean",
    "Byte",
    "byte",
    "Character",
    "char",
    "Double",
    "double",
    "Enum",
    "Float",
    "float",
    "Integer",
    "int",
    "Long",
    "long",
    "Number",
    #"Object",
    "Short",
    "short",
    "String",
    "Void"
]

JAVA_LANG_TYPES_MAPPER = {
    "Boolean": "boolean",
    "boolean": "Boolean",
    "Byte": "byte",
    "byte": "Byte",
    "Character": "char",
    "char": "Character",
    "Double": "double",
    "double": "Double",
    "Enum": "Enum",
    "Float": "float",
    "float": "Float",
    "Integer": "int",
    "int": "Integer",
    "Long": "long",
    "long": "Long",
    "Number": "Number",
    "Short": "Short",
    "short": "short",
    "String": "String",
    "Void": "Void"
}

# Algunas Clases de mockito incluidas en el paquete org.mockito
MOCKITO_ANNOTATIONS = [
    "Mock",
    "Spy",
    "Captor",
    "InjectMocks"
]

MOCKITO_CLASSES = [
    "BDDMockito",
    "Mockito",
    "MockedConstruction",
    "MockedStatic",
    "ArgumentCaptor",
    "AdditionalAnswers"
]

MOCKITO_METHODS = {
    # from class Mockito
    "mock": "Mockito",
    "spy": "Mockito",
    "when": "Mockito",
    "verify": "Mockito",
    "verifyNoInteractions": "Mockito",
    "verifyNoMoreInteractions": "Mockito",
    "mockStatic": "Mockito",
    "mockConstruction": "Mockito",
    "lenient": "Mockito",
    "inOrder": "Mockito",
    "ignoreStubs": "Mockito",
    "doThrow": "Mockito",
    "doReturn": "Mockito",
    "doNothing": "Mockito",
    "doCallRealMethod": "Mockito",
    "doAnswer": "Mockito",
    # from class BDDMockito
    "given": "BDDMockito",
    "then": "BDDMockito",
    "will": "BDDMockito",
    "willAnswer": "BDDMockito",
    "willCallRealMethod": "BDDMockito",
    "willDoNothing": "BDDMockito",
    "willReturn": "BDDMockito",
    "willThrow": "BDDMockito",
    # from class ArgumentCaptor
    "captor": "ArgumentCaptor",
    "forClass": "ArgumentCaptor",
    # from class AdditionalAnswers
    "answer": "AdditionalAnswers",
    "answersWithDelay": "AdditionalAnswers",
    "answerVoid": "AdditionalAnswers",
    "delegatesTo": "AdditionalAnswers",
    "returnsArgAt": "AdditionalAnswers",
    "returnsElementsOf": "AdditionalAnswers",
    "returnsFirstArg": "AdditionalAnswers",
    "returnsLastArg": "AdditionalAnswers",
    "returnsSecondArg": "AdditionalAnswers"
}

class DependencyParserUtils():

    @staticmethod
    def parse_potential_focal_and_external_dependencies(dependency_parser: DependencyClassParser, parsed_classes: dict, all_focal_java_files):
        classes_in_file = [clazz['class_name'] for clazz in parsed_classes]

        for parsed_class in parsed_classes:
            clazz = dict(parsed_class)
            imports = clazz['imports']
            package = clazz['package']
            class_name = clazz['class_name']
            class_fields = parsed_class['fields']
            class_methods = parsed_class['methods']

            #paths_imports_and_package, imports_not_in_project = get_path_imports(imports, package, class_name, classes_in_file, all_focal_java_files)
            paths_imports, paths_package, imports_not_in_project = DependencyParserUtils.get_path_imports(imports, package, all_focal_java_files)
            #print("\nimports_not_in_project = " + str(imports_not_in_project))
            #print("\n\n")
            #print("\npaths_imports = " + str(paths_imports))
            #print("\n\n")
            #print("\npaths_package = " + str(paths_package))
            #print("\n\n")

            for parsed_method in class_methods:
                #print("\n\n\n\n\n\n")
                method = dict(parsed_method)

                #print("\n\nMethod: " + method['full_signature'])

                class_fields_used = method['class_fields_used']
                class_method_references_used = method['class_method_references_used']
                class_methods_used = method['class_methods_used']


                extract_fields_from_class = DependencyParserUtils.get_used_fields_from_external_dependency(class_fields_used, class_fields, True)
                #class_metadata['new_fields'] = new_fields
                extract_methods_from_class, undefined_methods_from_class = DependencyParserUtils.get_methods_from_external_dependency(
                    class_methods_used, class_method_references_used, class_methods, True
                )
                
                parsed_method['used_private_signatures_of_class'] = [field['original_string'] for field in extract_fields_from_class if 'private' in field['modifier']]
                parsed_method['used_private_signatures_of_class'].extend([meth['full_signature_parameters'] + ";" for meth in extract_methods_from_class if 'private' in meth['modifiers']])
                
                parsed_method['used_non_private_signatures_of_class'] = [field['original_string'] for field in extract_fields_from_class if 'private' not in field['modifier']]
                #parsed_method['used_non_private_signatures_of_class'].extend([meth['full_signature_parameters'] + ";" for meth in class_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == True])
                parsed_method['used_non_private_signatures_of_class'].extend([meth['full_signature_parameters'] + ";" for meth in extract_methods_from_class if 'private' not in meth['modifiers']])
                parsed_method['used_non_private_signatures_of_class'].extend([meth + ";" for meth in undefined_methods_from_class])

                class_private_deps_used = {
                    'fields': [field for field in extract_fields_from_class if 'private' in field['modifier']],
                    'methods': [meth for meth in extract_methods_from_class if 'private' in meth['modifiers']]
                }

                #class_non_private_methods_used = [meth for meth in class_methods if 'private' not in meth['modifiers'] and meth['is_constructor'] == True]
                #class_non_private_methods_used.extend([meth for meth in extract_methods_from_class if 'private' not in meth['modifiers']])
                class_non_private_methods_used = [meth for meth in extract_methods_from_class if 'private' not in meth['modifiers']]
                #class_non_private_methods_used.extend([meth for meth in undefined_methods_from_class])
                class_non_private_deps_used = {
                    'fields': [field for field in extract_fields_from_class if 'private' not in field['modifier']],
                    'methods': class_non_private_methods_used,
                    'undefined_methods': undefined_methods_from_class
                }

                parsed_method['class_private_deps_used'] = class_private_deps_used
                parsed_method['class_non_private_deps_used'] = class_non_private_deps_used


                parsed_method.pop('class_fields_used')
                parsed_method.pop('class_method_references_used')
                parsed_method.pop('class_methods_used')
                #parsed_method.pop('var_declars')

                path_class = DependencyParserUtils.get_path_import_by_class_name(class_name, paths_package)
                used_external_dependencies = method['used_external_dependencies']

                signatures_of_used_external_dependencies = {}
                external_dependencies = []

                for ext_dep in used_external_dependencies:
                    #print("\n\n\n\nExtracting info from dependency: " + ext_dep)

                    fields_from_external_dependency = list()
                    if ext_dep in method['field_dependencies_by_class']:
                        fields_from_external_dependency.extend(method['field_dependencies_by_class'][ext_dep])
                    #print(f"\n\nfields_from_external_dependency = {str(fields_from_external_dependency)}")

                    method_references_from_external_dependency = list()
                    if ext_dep in method['method_references_dependencies_by_class']:
                        method_references_from_external_dependency.extend(method['method_references_dependencies_by_class'][ext_dep])
                    #print(f"\n\nmethod_references_from_external_dependency = {str(method_references_from_external_dependency)}")
                    
                    methods_from_external_dependency = dict()
                    if ext_dep in method['method_dependencies_by_class']:
                        method_dependencies = method['method_dependencies_by_class'][ext_dep]
                        for meth_dep in method_dependencies:
                            # Solo agregamos los que no están incluidos en la lista de method_references
                            # ya que de dicha lista se extraerán todos los métodos que concidan por nombre
                            if method_dependencies[meth_dep]['method_name'] not in method_references_from_external_dependency:
                                #methods_from_external_dependency.append(method_dependencies[meth_dep])
                                methods_from_external_dependency[meth_dep] = method_dependencies[meth_dep]
                    #print(f"\n\nmethods_from_external_dependency = {str(methods_from_external_dependency)}")

                    if (len(fields_from_external_dependency) == 0
                            and len(method_references_from_external_dependency) == 0
                            and not methods_from_external_dependency):
                        # Esta dependencia no tiene información para extraer
                        #print("Esta dependencia no tiene informacion para extraer: " + ext_dep)
                        continue


                    class_name_ext_dep = DependencyParserUtils.get_class_name(ext_dep)

                    if "." in class_name_ext_dep: # Por ejemplo, Map.Entry
                        continue

                    # Extrae info de dependencias especificadas en los imports
                    path_import = DependencyParserUtils.get_path_import_by_class_name(class_name_ext_dep, paths_imports)
                    path_in_package = DependencyParserUtils.get_path_import_by_class_name(class_name_ext_dep, paths_package)

                    if path_import is not None:
                        #print("Used path import: " + str(path_import))
                        DependencyParserUtils.extract_info_from_dependency(
                            dependency_parser, 
                            external_dependencies,
                            signatures_of_used_external_dependencies, 
                            path_import,
                            class_name_ext_dep,
                            ext_dep,
                            fields_from_external_dependency,
                            methods_from_external_dependency,
                            method_references_from_external_dependency
                        )
                    
                    if path_in_package is not None: # Clases en el mismo paquete
                        #print("\n\nUsed path in package: " + str(path_in_package) + "\n\n")
                        DependencyParserUtils.extract_info_from_dependency(
                            dependency_parser, 
                            external_dependencies,
                            signatures_of_used_external_dependencies, 
                            path_in_package,
                            class_name_ext_dep,
                            ext_dep,
                            fields_from_external_dependency,
                            methods_from_external_dependency,
                            method_references_from_external_dependency
                        )
                    
                    if path_class is not None and class_name_ext_dep in classes_in_file: # Clases en el mismo file
                        #print("\n\nUsed path in package: " + str(class_name_ext_dep) + "\n\n")
                        DependencyParserUtils.extract_info_from_dependency(
                            dependency_parser, 
                            external_dependencies,
                            signatures_of_used_external_dependencies, 
                            path_class,
                            class_name_ext_dep,
                            ext_dep,
                            fields_from_external_dependency,
                            methods_from_external_dependency,
                            method_references_from_external_dependency
                        )
                        
                    #else:
                        #print("Class Import not in project: " + str(class_name_ext_dep))
                        #signatures_of_used_external_dependencies.setdefault(ext_dep, [])
                    
                #empty_dependencies = []
                #for dependency in signatures_of_used_external_dependencies:
                #    if len(signatures_of_used_external_dependencies[dependency]) == 0:
                #        empty_dependencies.append(dependency)
                        
                #for empty_dep in empty_dependencies:
                #    signatures_of_used_external_dependencies.pop(empty_dep)

                parsed_method['signatures_of_external_dependencies'] = signatures_of_used_external_dependencies
                parsed_method['external_dependencies'] = external_dependencies

                parsed_method.pop('use_some_field')
                parsed_method.pop('var_declars')
                parsed_method.pop('used_external_dependencies')
                parsed_method.pop('methods_from_external_dependencies')
                parsed_method.pop('method_references_from_external_dependencies')
                parsed_method.pop('fields_from_external_dependencies')
                parsed_method.pop('method_dependencies_by_class')
                parsed_method.pop('method_references_dependencies_by_class')
                parsed_method.pop('field_dependencies_by_class')
                parsed_method.pop('undefined_method_dependencies')
                parsed_method.pop('class_methods_that_invoke_other_methods')
                
            #print("\n\n")
            #print(parsed_class)
            #print("\n\n")
                

        #print("\n\n")
        return parsed_classes
    

    @staticmethod
    def get_class_name(cadena) -> str:
        cadena = cadena.split("[")[0]
        return cadena.split("<")[0]


    @staticmethod
    def get_path_import_by_class_name(class_name: str, path_imports) -> bool:
        for path in path_imports:
            if path.endswith("/" + class_name + ".java"):
                return path
        return None
    

    @staticmethod
    def extract_info_from_dependency(dependency_parser: DependencyClassParser, 
                                     external_dependencies: list[dict],
                                     signatures_of_used_external_dependencies: dict, 
                                     path_file: str,
                                     class_name_ext_dep: str,
                                     ext_dep: str,
                                     fields_from_external_dependency: list,
                                     methods_from_external_dependency: dict,
                                     method_references_from_external_dependency: list):

        parsed_class_ext_dep = dependency_parser.parse_file(
            path_file,
            class_name_ext_dep,
            ext_dep
        )
        
        #if class_name_ext_dep == 'ObjectConstructor':
        #    print("\n\n")
        #    print(path_file)
        #    print(parsed_class_ext_dep)
        #    print("\n\n")
        
        if parsed_class_ext_dep is None:
            return
        
        class_signature = parsed_class_ext_dep['class_signature']
        signatures_of_used_external_dependencies.setdefault(class_signature, [])
        
        dependency_fields = DependencyParserUtils.get_used_fields_from_external_dependency(fields_from_external_dependency, parsed_class_ext_dep['fields'])
        #parsed_class_ext_dep['new_fields'] = dependency_fields_signatures

        for field in dependency_fields:
            if field['original_string'] not in signatures_of_used_external_dependencies[class_signature]:
                signatures_of_used_external_dependencies[class_signature].append(field['original_string'])
        

        constructors = [m for m in parsed_class_ext_dep['methods'] if m['is_constructor'] == True and 'private' not in m['modifiers']]
        for cons in constructors:
            if cons['full_signature_parameters'] + ";" not in signatures_of_used_external_dependencies[class_signature]:
                signatures_of_used_external_dependencies[class_signature].append(cons['full_signature_parameters'] + ";")
        

        extract_methods_from_dependency, undefined_methods_from_dependency = DependencyParserUtils.get_methods_from_external_dependency(
            methods_from_external_dependency, method_references_from_external_dependency, parsed_class_ext_dep['methods']
        )

        #parsed_class_ext_dep['new_methods'] = extract_methods_from_dependency
        #parsed_class_ext_dep['new_undefined_methods'] = undefined_methods_from_dependency

        for meth in extract_methods_from_dependency:
            if meth['full_signature_parameters'] + ";" not in signatures_of_used_external_dependencies[class_signature]:
                signatures_of_used_external_dependencies[class_signature].append(meth['full_signature_parameters'] + ";")
        
        for meth in undefined_methods_from_dependency:
            if meth + ";" not in signatures_of_used_external_dependencies[class_signature]:
                signatures_of_used_external_dependencies[class_signature].append(meth + ";")


        dependency_already_exists = False
        for ext_dep in external_dependencies:
            if ext_dep['class_signature'] == class_signature:
                dependency_already_exists = True

                for dep_field in dependency_fields:
                    field_already_exists = False
                    for field in ext_dep['fields']:
                        #if dep_field['var_name'] == field['var_name']:
                        if dep_field['original_string'] == field['original_string']:
                            field_already_exists = True
                            break
                    if field_already_exists == False:
                        ext_dep['fields'].append(dep_field)
                
                dependency_methods = [c for c in constructors]
                dependency_methods.extend(extract_methods_from_dependency)

                for dep_method in dependency_methods:
                    method_already_exists = False
                    for method in ext_dep['methods']:
                        if dep_method['full_signature_parameters'] == method['full_signature_parameters']:
                            method_already_exists = True
                            break
                    if method_already_exists == False:
                        ext_dep['methods'].append(dep_method)
                
                ext_dep['undefined_methods'].extend(undefined_methods_from_dependency)

        
        if dependency_already_exists == False:
            methods_list = [c for c in constructors]
            methods_list.extend(extract_methods_from_dependency)

            ext_dep_metadata = {
                'class_name': parsed_class_ext_dep['class_name'],
                'external_dependency' : parsed_class_ext_dep['external_dependency'],
                'class_signature': parsed_class_ext_dep['class_signature'],
                'has_constructor': parsed_class_ext_dep['has_constructor'],
                'fields': dependency_fields,
                'methods': methods_list,
                'undefined_methods': undefined_methods_from_dependency
            }
            external_dependencies.append(ext_dep_metadata)

        #print("\n\n")
        #print(parsed_class_ext_dep)
        #print("\n\n")
    

    @staticmethod
    def get_path_imports(imports: list, package: str, java_files):
        imports_norm = set()
        package_norm = package.replace(";", "").replace("package ", "").replace(".", "/").strip()
        imports_norm_with_wildcard = set()

        #print("\n\nImports: " + str(imports))

        for _import in imports:
            _imp = _import.replace(";", "").strip()
            #_imp = _imp.strip()

            if _imp.startswith("import static "):
                _imp = _imp.replace("import static ", "").strip()
                #_imp = _imp.strip()
                packs = _imp.split(".")
                packs.pop() # Eliminamos el último elemento que es el método o variable estática
                _imp = ".".join(packs)
            else:
                _imp = _imp.replace("import ", "").strip()
                if _imp.endswith("*"): # Por ejemplo, com.eljavatar.package.*
                    packs = _imp.split(".")
                    packs.pop() # Eliminamos el último elemento que es el *
                    package_wildcard = "/".join(packs)
                    imports_norm_with_wildcard.add(package_wildcard)
                    continue
                #_imp = _imp.strip()

            _imp = _imp.replace(".", "/")
            _imp = _imp + ".java"
            imports_norm.add(_imp)
        

        paths_package = set()
        for file in java_files:
            #if file.endswith(class_name + ".java"):
                # Omitimos porque no queremos obtener la misma clase que ya se inspeccionó
                #continue

            directories = file.split("/")
            last_directory = "/".join(directories[:-1]).strip() # Quitamos el archivo .java para evaluar solo el path
            if last_directory.endswith(package_norm):
                paths_package.add(file.strip())
        

        imports_not_in_project = set()
        paths_imports_with_wildcard = set()
        for import_package in imports_norm_with_wildcard:
            import_is_in_project = False
            for file in java_files:
                directories = file.split("/")
                last_directory = "/".join(directories[:-1]).strip() # Quitamos el archivo .java para evaluar solo el path
                
                if last_directory.endswith(import_package):
                    paths_imports_with_wildcard.add(file.strip())
                    import_is_in_project = True
            
            if import_is_in_project == False:
                # Obtenemos el import en formato de packages
                _imp_norm = import_package.replace("/", ".")
                _imp_norm = _imp_norm + ".*"
                
                imports_not_in_project.add(_imp_norm)


        #print("\npackage = " + str(package_norm))
        #print("\npaths_package = " + str(paths_package))

        paths_imports = set()
        for imp_norm in imports_norm:
            import_is_in_project = False
            for file in java_files:
                _file = file.strip()
                #if _file.endswith(class_name + ".java"):
                    # Omitimos en caso de que haya una clase con el mismo nombre en otro paquete
                #    import_is_in_project = True
                #    continue

                if _file.endswith(imp_norm):
                    paths_imports.add(_file)
                    import_is_in_project = True
                    break
            
            if import_is_in_project == False:
                # Obtenemos el import en formato de packages
                _imp_norm = imp_norm.replace("/", ".").replace(".java", "")
                
                imports_not_in_project.add(_imp_norm)
        

        paths_imports.update(paths_imports_with_wildcard)


        # Mergeamos las listas de paths, dando preferencia a las clases de los imports
        paths_imports_and_package = paths_imports
        for path_pack in paths_package:
            dirs_pack = path_pack.split("/")
            class_pack = dirs_pack[-1]
            are_same_name_class = False

            for path_imp in paths_imports:
                dirs_imp = path_imp.split("/")
                class_imp = dirs_imp[-1]
                if class_pack == class_imp:
                    are_same_name_class = True
            
            if are_same_name_class == False:
                paths_imports_and_package.add(path_pack)
        
        #return sorted(list(paths_imports_and_package)), sorted(list(imports_not_in_project))
        return sorted(list(paths_imports)), sorted(list(paths_package)), sorted(list(imports_not_in_project))


    @staticmethod
    def get_used_fields_from_external_dependency(fields_from_external_dependency: list, class_fields: list, allow_private: bool = False):
        new_fields = list()
        #print("\nfields = " + str(class_metadata['fields']) + "\n")
        for field in class_fields:
            #private_validator = permit_private if permit_private else 'private' not in field['modifier']
            if (field['var_name'] in fields_from_external_dependency 
                    and (allow_private or 'private' not in field['modifier'])):
                new_fields.append(field)
        
        #print("\nfields_new = " + str(new_fields) + "\n")
        return new_fields
    

    @staticmethod
    def get_methods_from_external_dependency(methods_from_external_dependency: dict,
                                             method_references_from_external_dependency: list, 
                                             class_methods: list,
                                             allow_private: bool = False):
        
        extract_methods_from_dependency = list()
        undefined_methods_from_dependency = set()

        for method in class_methods:
            if (method['method_name'] in method_references_from_external_dependency
                    and (allow_private or 'private' not in method['modifiers'])):
                extract_methods_from_dependency.append(method)
                continue

        #print("\n")
        #print("extract_methods_from_dependency = " + str(extract_methods_from_dependency))
        #print("\n")

        for meth_from_dependency_sig in methods_from_external_dependency:
            meth_from_dependency = methods_from_external_dependency[meth_from_dependency_sig]
            meth_from_dependency_name = meth_from_dependency['method_name']
            meth_from_dependency_parameters_list = meth_from_dependency['parameters_list']

            #print("\n\n\nmeth_from_dependency_sig = " + meth_from_dependency_sig)

            methods_matching = list()
            for meth in class_methods:
                if (meth['method_name'] == meth_from_dependency_name 
                        and (allow_private or 'private' not in meth['modifiers'])
                        and len(meth['parameters_list']) == len(meth_from_dependency_parameters_list)):
                    methods_matching.append(meth)
            
            #print("Methods matching: " + str(len(methods_matching)))

            if len(methods_matching) == 0:
                # Ningún método hace match por nombre y cantidad de parámetros con el método de la dependencia externa
                # (probablemente es un método heredado) por lo cual no podemos obtener la información de dicho método
                #print("No selecciono nada por cantidad de parametros para el metodo: " + meth_from_dependency_sig)
                undefined_methods_from_dependency.add(meth_from_dependency_sig)
                continue

            if len(methods_matching) == 1:
                #print("Selecciono porque solo existe un metodo que coincide por nombre y cantidad de parametros: " + methods_matching[0]['signature'])
                #extract_methods_from_dependency.append(methods_matching[0])
                DependencyParserUtils.add_method_matching(extract_methods_from_dependency, undefined_methods_from_dependency, methods_matching[0], meth_from_dependency_sig)
                continue

            methods_partial_matching = list()
            has_method_matching = False

            for meth_match in methods_matching:
                #print("\n\nValido contra metodo: " + meth_match['signature'])
                parameters_list = meth_match['parameters_list']
                count_params_matching = 0
                count_params_partial_matching = 0
                
                for index, param_meth_dep in enumerate(meth_from_dependency_parameters_list):
                    param = parameters_list[index]
                    
                    if param_meth_dep == param:
                        count_params_matching += 1
                        count_params_partial_matching += 1
                    else:
                        if (param_meth_dep in JAVA_LANG_CLASSES_TYPES 
                                and param in JAVA_LANG_CLASSES_TYPES
                                and param == JAVA_LANG_TYPES_MAPPER[param_meth_dep]):
                            #print(f"Coinciden por wrappers -> param_caller: {param_caller} - param: {param}")
                            count_params_matching += 1
                            count_params_partial_matching += 1
                            continue
                        
                        if "[" in param_meth_dep and "[" in param:
                            _param_meth_dep = param_meth_dep.split("[")[0] # int
                            _param = param.split("[")[0] # Integer

                            if (_param_meth_dep in JAVA_LANG_CLASSES_TYPES 
                                    and _param in JAVA_LANG_CLASSES_TYPES
                                    and _param == JAVA_LANG_TYPES_MAPPER[_param_meth_dep]):
                                #print(f"Coinciden por wrappers de tipo array-> param_caller: {param_caller} - param: {param}")
                                count_params_matching += 1
                                count_params_partial_matching += 1
                                continue

                        if "<" in param_meth_dep and "<" in param:
                            _param_meth_dep = param_meth_dep.split("<")[0]
                            _param = param.split("<")[0]

                            if _param_meth_dep == _param:
                                #print(f"Coinciden por tipo de dato generico-> param_caller: {param_caller} - param: {param}")
                                count_params_matching += 1
                                count_params_partial_matching += 1
                                continue
                        
                        if param_meth_dep == "unknownType":
                            count_params_partial_matching += 1
                            continue
                            # A         -> A
                            # undefined -> B
                            # C         -> C
                            # undefined -> E

                            # A         -> A
                            # undefined -> D
                            # C         -> C
                            # undefined -> E
                
                if count_params_matching == len(parameters_list):
                    #print("Selecciono porque Todos los parametros coinciden con = " + meth_match['signature'])
                    DependencyParserUtils.add_method_matching(extract_methods_from_dependency, undefined_methods_from_dependency, meth_match, meth_from_dependency_sig)
                    has_method_matching = True
                    break
                
                if count_params_partial_matching == len(parameters_list):
                    #print(f"Selecciono porque El metodo {meth_from_dependency_sig} tiene parametos indefinidos, y coincide parcialmente con {meth_match['signature']}")
                    DependencyParserUtils.add_method_matching(extract_methods_from_dependency, undefined_methods_from_dependency, meth_match, meth_from_dependency_sig)
                    has_method_matching = True
                    methods_partial_matching.append(meth_match)
            
            #print("\n\nmethods_partial_matching = " + str(len(methods_partial_matching)) + "\n")

            if has_method_matching == False:
                #print("Lo inserto en undefined_methods_from_dependency 0002")
                undefined_methods_from_dependency.add(meth_from_dependency_sig)
        
        return extract_methods_from_dependency, sorted(list(undefined_methods_from_dependency))


    @staticmethod
    def add_method_matching(extract_methods_from_dependency: list, undefined_methods_from_dependency: set, method_to_add: dict, meth_from_dependency_sig: str):
        already_exists_method = False
        for meth in extract_methods_from_dependency:
            if meth['parameters'] == method_to_add['parameters']:
                already_exists_method = True
                break
        
        if already_exists_method == False:
            extract_methods_from_dependency.append(method_to_add)
            #if 'private' not in method_to_add['modifiers']:
            #    extract_methods_from_dependency.append(method_to_add)
            #else:
            #    print("Lo inserto en undefined_methods_from_dependency 0001")
            #    undefined_methods_from_dependency.add(meth_from_dependency_sig)