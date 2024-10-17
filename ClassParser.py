import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from typing import List, Dict, Any, Set, Optional
from packaging import version
import pkg_resources

from dependency_parser_utils import (
    JAVA_LANG_CLASSES_TYPES,
    JAVA_LANG_TYPES_MAPPER,
    MOCKITO_ANNOTATIONS,
    MOCKITO_CLASSES,
    MOCKITO_METHODS
)

class ClassParser():

    def __init__(self, language):
        tree_sitter_version = pkg_resources.get_distribution("tree_sitter").version

        if version.parse(str(tree_sitter_version)) < version.parse("0.22.0"):
            JAVA_LANGUAGE = Language(tsjava.language(), language)
        else:
            JAVA_LANGUAGE = Language(tsjava.language())

        self.parser = Parser()
        self.parser.set_language(JAVA_LANGUAGE)
    

    def parse_file(self, file):
        """
        Parses a java file and extract metadata of all the classes and methods defined
        """

        #if ("/FileWorkUnitCalculator" not in file):
        #    return []

        #Build Tree
        with open(file, 'r') as content_file:
            try: 
                content = content_file.read()
                self.content = content
            except:
                return list()
        
        #print("\n\n\n")
        #print(content)
        #print("\n\n\n")
        
        #print(self.content)
        # Esto retorna las posiciones (por línea y posición de caracter) de cada uno de los nodos en el árbol de sintaxis
        tree = self.parser.parse(bytes(content, "utf8"))
        #tree = self.parser.parse(bytes(content, "cp1252"))

        root_node = tree.root_node
        has_error = root_node.has_error
        #print("\n\n\n")
        #print("HAS ERROR: " + str(has_error))
        #print("\n\n\n")
        if has_error: # Solo mapeamos codigo que tenga sintaxis correcta
            return []

        package_declaration = (node for node in tree.root_node.children if node.type == 'package_declaration')
        classes = (node for node in tree.root_node.children if node.type == 'class_declaration')
        imports = (node for node in tree.root_node.children if node.type == 'import_declaration')
        #print(tree.root_node.sexp())

        import_list = list()
        for _import in imports:
            import_list.append(_import.text.decode().lstrip("b'"))

        static_imports = ClassParser.get_static_imports(import_list)
        class_imports = ClassParser.get_class_imports(import_list)

        #print("\nStatic imports: " + str(static_imports))
        #print("Class imports: " + str(class_imports))
        
        #Parsed Classes
        parsed_classes = list()

        #print("\n\nShowing class_metadata:")

        #Classes
        for _class in classes:
            #Class metadata
            #class_identifier = Nombre de la clase
            class_identifier = self.match_from_span([child for child in _class.children if child.type == 'identifier'][0], content).strip()
            class_metadata = self.get_class_metadata(_class, content)

            #print("\nClass name: " + class_identifier)

            fields_using_mockito_annotations = ClassParser.get_fields_using_mockito_annotations(class_metadata['fields'])

            methods = list()
            
            class_metadata['has_constructor'] = False
            #Parse methods
            for child in (child for child in _class.children if child.type == 'class_body'):
                for _, node in enumerate(child.children):
                    if node.type == 'method_declaration' or node.type == 'constructor_declaration':
                        if node.type == 'constructor_declaration':
                            class_metadata['has_constructor'] = True
                        
                        #Read Method metadata
                        method_metadata = ClassParser.get_function_metadata(class_identifier, static_imports, class_imports, fields_using_mockito_annotations, node, class_metadata['fields'], content)
                        methods.append(method_metadata)
                        #print("\n\n\n\n")       

            ClassParser.get_class_methods_that_invoke_other_methods(methods, class_identifier)
            
            class_metadata['methods'] = methods
            class_metadata['imports'] = import_list
            class_metadata['package'] = ""
            for _package in package_declaration:
                class_metadata['package'] = _package.text.decode().lstrip("b'")
            
            #print("\n\n")
            #print(class_metadata)
            #print("\n\n")
            parsed_classes.append(class_metadata)
        
        return parsed_classes
    

    @staticmethod
    def get_class_methods_that_invoke_other_methods(methods: list, class_name: str):
        for method in methods:
            if method['class_methods_that_invoke_other_methods']:
                class_methods_that_invoke_other_methods = method['class_methods_that_invoke_other_methods']

                #print("\n\n\n")
                #print("method with dependencies in same class:")
                #print(method)
                #print("\n\nclass_methods_that_invoke_other_methods:")
                #print(class_methods_that_invoke_other_methods)
                #print("\n\n\n")
                
                for meth_caller_sig in class_methods_that_invoke_other_methods:
                    method_caller = class_methods_that_invoke_other_methods[meth_caller_sig]
                    #print("\n Method caller = " + meth_caller_sig + " -> " + str(method_caller))
                    method_name_caller = method_caller['method_name_caller']
                    parameters_list_caller = method_caller['parameters_list_caller']
                    methods_invocated = method_caller['methods_invocated']

                    methods_matching = list()
                    for meth in methods:
                        if meth['method_name'] == method_name_caller and len(meth['parameters_list']) == len(parameters_list_caller):
                            methods_matching.append(meth)
                    
                    #print("Methods matching: " + str(len(methods_matching)))

                    if len(methods_matching) == 0:
                        # Ningún método hace match por nombre y cantidad de parámetros con el método invocador
                        # (probablemente es un método heredado) por lo cual no podemos saber a qué dependencia
                        # pertenencen los métodos invocados
                        #print("No selecciono nada por cantidad de parametros para el metodo: " + meth_caller_sig)
                        for meth_invocated in methods_invocated:
                            if meth_invocated not in method['undefined_method_dependencies']:
                                method['undefined_method_dependencies'].append(meth_invocated)
                        continue

                    method_caller_matching = None

                    if len(methods_matching) == 1:
                        #print("\nSelecciono porque solo existe un metodo que coincide por nombre y cantidad de parametros: " + methods_matching[0]['signature'])
                        method_caller_matching = methods_matching[0]
                    
                    else:
                        methods_partial_matching = list()
                        type_returns_methods_partial_matching = set()
                        for meth_match in methods_matching:
                            #print("\n\nValido metodo: " + meth_match['signature'])
                            type_return_meth = meth_match['return']
                            parameters_list = meth_match['parameters_list']
                            count_params_matching = 0
                            count_params_partial_matching = 0
                            
                            for index, param_caller in enumerate(parameters_list_caller):
                                param = parameters_list[index]
                                
                                if param_caller == param:
                                    count_params_matching += 1
                                    count_params_partial_matching += 1
                                else:
                                    if (param_caller in JAVA_LANG_CLASSES_TYPES 
                                            and param in JAVA_LANG_CLASSES_TYPES
                                            and param == JAVA_LANG_TYPES_MAPPER[param_caller]):
                                        #print(f"Coinciden por wrappers -> param_caller: {param_caller} - param: {param}")
                                        count_params_matching += 1
                                        count_params_partial_matching += 1
                                        continue
                                    
                                    if "[" in param_caller and "[" in param:
                                        _param_caller = param_caller.split("[")[0] # int
                                        _param = param.split("[")[0] # Integer

                                        if (_param_caller in JAVA_LANG_CLASSES_TYPES 
                                                and _param in JAVA_LANG_CLASSES_TYPES
                                                and _param == JAVA_LANG_TYPES_MAPPER[_param_caller]):
                                            #print(f"Coinciden por wrappers de tipo array-> param_caller: {param_caller} - param: {param}")
                                            count_params_matching += 1
                                            count_params_partial_matching += 1
                                            continue

                                    if "<" in param_caller and "<" in param:
                                        _param_caller = param_caller.split("<")[0]
                                        _param = param.split("<")[0]

                                        if _param_caller == _param:
                                            #print(f"Coinciden por tipo de dato generico-> param_caller: {param_caller} - param: {param}")
                                            count_params_matching += 1
                                            count_params_partial_matching += 1
                                            continue
                                    
                                    if param_caller == "unknownType":
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
                                #print("Todos los parametros coinciden con = " + meth_match['signature'])
                                method_caller_matching = meth_match
                                break
                            
                            if count_params_partial_matching == len(parameters_list):
                                #print("Tiene parametos indefinidos")
                                methods_partial_matching.append(meth_match)
                                type_returns_methods_partial_matching.add(type_return_meth)
                        
                        #print("\n\nmethods_partial_matching = " + str(len(methods_partial_matching)))

                        if len(methods_partial_matching) == 1 or len(type_returns_methods_partial_matching) == 1:
                            # Solo debería haber un método que coincida parcialmente (con parámetros unknownType)
                            # o si hay más de uno, todos deberían retornar el mismo tipo de dato
                            #print("Selecciono porque solo existe un metodo que coincide parcialmente por nombre y cantidad de parametros: " + methods_partial_maching[0]['signature'])
                            method_caller_matching = methods_partial_matching[0]

                    #print("\n\nmethod_caller_matching = " + str(method_caller_matching))

                    if method_caller_matching is not None: # Se encontró un método que coincide
                        #print("\nSelecciono metodo que matchea = " + str(method_caller_matching))
                        type_return_method = method_caller_matching['return']

                        if type_return_method in JAVA_LANG_CLASSES_TYPES:
                            continue

                        if type_return_method == class_name:
                            for meth_invocated in methods_invocated:
                                if meth_invocated not in method['class_methods_used']:
                                    #method['class_methods_used'][type_return_method][meth_invocated] = {}
                                    #method['class_methods_used'][type_return_method][meth_invocated]['method_name'] = methods_invocated[meth_invocated]['method_name_invocated']
                                    #method['class_methods_used'][type_return_method][meth_invocated]['parameters_list'] = methods_invocated[meth_invocated]['parameters_list_invocated']

                                    method['class_methods_used'][meth_invocated] = {}
                                    method['class_methods_used'][meth_invocated]['method_name'] = methods_invocated[meth_invocated]['method_name_invocated']
                                    method['class_methods_used'][meth_invocated]['parameters_list'] = methods_invocated[meth_invocated]['parameters_list_invocated']
                            continue
                                
                        if type_return_method not in method['used_external_dependencies']:
                            method['used_external_dependencies'].append(type_return_method)
                            method['method_dependencies_by_class'].setdefault(type_return_method, {})
                            for meth_invocated in methods_invocated:
                                method['methods_from_external_dependencies'].append(type_return_method + "." + meth_invocated)
                                method['method_dependencies_by_class'][type_return_method][meth_invocated] = {}
                                method['method_dependencies_by_class'][type_return_method][meth_invocated]['method_name'] = methods_invocated[meth_invocated]['method_name_invocated']
                                method['method_dependencies_by_class'][type_return_method][meth_invocated]['parameters_list'] = methods_invocated[meth_invocated]['parameters_list_invocated']
                        else:
                            method['method_dependencies_by_class'].setdefault(type_return_method, {})
                            for meth_invocated in methods_invocated:
                                if meth_invocated not in method['method_dependencies_by_class'][type_return_method]:
                                    method['methods_from_external_dependencies'].append(type_return_method + "." + meth_invocated)
                                    method['method_dependencies_by_class'][type_return_method][meth_invocated] = {}
                                    method['method_dependencies_by_class'][type_return_method][meth_invocated]['method_name'] = methods_invocated[meth_invocated]['method_name_invocated']
                                    method['method_dependencies_by_class'][type_return_method][meth_invocated]['parameters_list'] = methods_invocated[meth_invocated]['parameters_list_invocated']

                    else:
                        # No podemos acceder al método invocador de la clase (probablemente porque hay más de un
                        # método que coincide parcialmente con la cantidad y tipo de parámetros (casos unknownType)
                        # que retornan distinto tipo de dato), por lo cual no podemos saber
                        # a qué dependencia pertenencen los métodos invocados
                        #print("Marco como undefined porque hay varios matching = ")
                        for meth_invocated in methods_invocated:
                            if meth_invocated not in method['undefined_method_dependencies']:
                                method['undefined_method_dependencies'].append(meth_invocated)
                    
                #method.pop('class_methods_that_invoke_other_methods') # Aún no elimino esta key
    

    @staticmethod
    def get_class_metadata(class_node, blob: str):
        """
        Extract class-level metadata 
        """
        metadata = {
            'class_name': '',
            'superclass': '',
            'interfaces': '',
            'class_signature': '',
            'class_modifier': '',
            'has_constructor': '',
            'fields': '',
            #'class_use_mockito_annotations': False,
            'argument_list': '',
            #'methods_signature': '',
            'methods': '',
        }

        #Superclass
        superclass = class_node.child_by_field_name('superclass')
        if superclass:
            metadata['superclass'] = ClassParser.match_from_span(superclass, blob)
        
        #Interfaces
        interfaces = class_node.child_by_field_name('interfaces')
        if interfaces:
            metadata['interfaces'] = ClassParser.match_from_span(interfaces, blob)
        
        metadata['class_signature'] = ClassParser.get_class_full_signature(class_node, blob)

        #Modifier
        modifiers_node_list = ClassParser.children_of_type(class_node, "modifiers")
        if len(modifiers_node_list) > 0:
            modifiers_node = modifiers_node_list[0]
            metadata["class_modifier"] = ' '.join(ClassParser.match_from_span(modifiers_node, blob).split())
            for modifier_child in modifiers_node.children:
                if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                    #line_comment_str = ClassParser.match_from_span(modifier_child, blob)
                    line_comment_str = modifier_child.text.decode("utf-8")
                    #print("\n\n")
                    #print(f"Comment in class modifier {metadata['modifiers']} => {line_comment_str}")
                    #print("\n\n")
                    metadata['class_modifier'] = metadata['class_modifier'].replace(line_comment_str, "").strip()

                    metadata['class_signature'] = metadata['class_signature'].replace(line_comment_str, "").strip()
        else:
            metadata["class_modifier"] = ""
        
        #Fields
        fields = ClassParser.get_class_fields(class_node, blob)
        metadata['fields'] = fields

        #Identifier and Arguments
        is_header = False
        for n in class_node.children:
            if is_header:
                if n.type == 'identifier':
                    metadata['class_name'] = ClassParser.match_from_span(n, blob).strip('(:')
                elif n.type == 'argument_list':
                    metadata['argument_list'] = ClassParser.match_from_span(n, blob)
            if n.type == 'class':
                is_header = True
            elif n.type == ':':
                break
        return metadata
    

    @staticmethod
    def get_class_fields(class_node, blob: str):
        """
        Extract metadata for all the fields defined in the class
        """
        
        body_node = class_node.child_by_field_name("body")
        fields = []
        
        for f in ClassParser.children_of_type(body_node, "field_declaration"):
            field_dict = {}

            #Complete field
            field_dict["original_string"] = ClassParser.match_from_span(f, blob)

            #Modifier
            modifiers_node_list = ClassParser.children_of_type(f, "modifiers")
            if len(modifiers_node_list) > 0:
                modifiers_node = modifiers_node_list[0]
                #field_dict["modifier"] = ClassParser.match_from_span(modifiers_node, blob)
                field_dict["modifier"] = ' '.join(ClassParser.match_from_span(modifiers_node, blob).split())
                for modifier_child in modifiers_node.children:
                    if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                        #line_comment_str = ClassParser.match_from_span(modifier_child, blob)
                        line_comment_str = modifier_child.text.decode("utf-8")
                        #print("\n\n")
                        #print(f"Comment in field modifier {field_dict['modifiers']} => {line_comment_str}")
                        #print("\n\n")
                        field_dict['modifier'] = field_dict['modifier'].replace(line_comment_str, "").strip()
            else:
                field_dict["modifier"] = ""

            if ClassParser.field_contains_mockito_annotations(field_dict["modifier"]):
                field_dict["field_use_mockito_annotations"] = True
            else:
                field_dict["field_use_mockito_annotations"] = False

            #Type
            type_node = f.child_by_field_name("type")
            var_type = ClassParser.match_from_span(type_node, blob)
            field_dict["type"] = var_type.replace(" ", "")

            #Declarator
            declarator_node = f.child_by_field_name("declarator")
            field_dict["declarator"] = ClassParser.match_from_span(declarator_node, blob)
            
            #Var name
            var_node = declarator_node.child_by_field_name("name")
            field_dict["var_name"] = ClassParser.match_from_span(var_node, blob)

            fields.append(field_dict)

        return fields
    

    @staticmethod
    def field_contains_mockito_annotations(modifiers: str):
        for class_annotation in MOCKITO_ANNOTATIONS:
            annotation = "@" + class_annotation
            if annotation in modifiers:
                return True
        
        return False
    

    @staticmethod
    def get_fields_using_mockito_annotations(fields: list):
        fields_using_mockito_annotations = list()
        for field in fields:
            if field['field_use_mockito_annotations'] == True:
                fields_using_mockito_annotations.append(field['var_name'])
        
        return fields_using_mockito_annotations


    @staticmethod
    def get_function_metadata(class_identifier, 
                              static_imports: dict, 
                              class_imports: list,
                              fields_using_mockito_annotations: list, 
                              function_node, 
                              class_fields, 
                              blob: str):
        """
        Extract method-level metadata 
        """		
        metadata = {
            'method_name': '',
            'parameters': '',
            'parameters_list': [],
            'modifiers': '',
            'type_parameters': '',
            'return' : '',
            'body': '',
            'class': '',
            'signature': '',
            'full_signature': '',
            'full_signature_parameters': '',
            'class_method_signature': '',
            'is_testcase': '',
            'test_use_mockito': False,
            'is_constructor': '',
            'is_get_or_set': '',
            'use_some_field': '',
            'class_fields_used': [],
            'class_methods_used': [],
            'class_method_references_used': [],
            'var_declars': '',
            #'invocations': '',
            'used_external_dependencies': '',
            'methods_from_external_dependencies': '',
            'method_references_from_external_dependencies': '',
            'fields_from_external_dependencies': '',
            'method_dependencies_by_class': '',
            'method_references_dependencies_by_class': '',
            'field_dependencies_by_class': '',
            'field_dependencies_by_class': '',
            'undefined_method_dependencies': '',
            'class_methods_that_invoke_other_methods': {}
        }

        #Body
        metadata['body'] = ClassParser.match_from_span(function_node, blob)
        metadata['class'] = class_identifier

        #print("\n\n\n")
        #print(metadata['body'])
        #print("\n\n\n")

        # Parameters
        full_parameter_list, dependent_classes, instance_2_classes = ClassParser.get_method_name_and_params(function_node, metadata, blob)
        full_parameters_str = ' '.join(full_parameter_list)

        # Add field dependencies
        dependent_classes, instance_2_classes =  ClassParser.get_field_dependencies(dependent_classes, instance_2_classes, class_fields)

        # Add class dependencies from object_creation an array_creation
        dependent_classes = ClassParser.get_dependencies_from_object_creation(function_node, dependent_classes, blob)

        #Is getter or setter
        metadata['is_get_or_set'] = ClassParser.is_getter_or_setter(function_node, class_fields, metadata['parameters_list'])

        #Use Class fields or not
        #if metadata['is_get_or_set'] == True:
        if metadata['is_get_or_set'] == True and function_node.type != 'constructor_declaration':
            metadata['use_some_field'] = True
        else:
            metadata['use_some_field'] = ClassParser.use_fields(function_node.child_by_field_name('body'), metadata, class_fields, blob)

        #Is Constructor
        metadata['is_constructor'] = False
        #if "constructor" in function_node.type:
        if function_node.type == 'constructor_declaration':
            metadata['is_constructor'] = True

        #Test Case
        modifiers_node_list = ClassParser.children_of_type(function_node, "modifiers")
        metadata['is_testcase'] = False
        for m in modifiers_node_list:
            modifier = ClassParser.match_from_span(m, blob)
            if '@Test' in modifier:
                metadata['is_testcase'] = True
        

        var_declars = ClassParser.get_var_declar(function_node, instance_2_classes, blob)
        #var_declars = ClassParser.get_invocations_into_statements(function_node, var_declars, blob)
        metadata['var_declars'] = var_declars
        # Complete dependent_classes with vae_declars
        for value in var_declars.values():
            dtype = value.split("[")[0]
            if dtype not in dependent_classes:
                dependent_classes.append(dtype)
        

        #Method Invocations
        metadata['static_methods_used'] = []
        ClassParser.get_method_m_deps(function_node, class_identifier, static_imports, metadata, var_declars, dependent_classes, instance_2_classes, class_fields, blob)

        # Used method references from external dependencies
        ClassParser.get_method_m_refs_deps(function_node, class_identifier, class_imports, metadata, var_declars, dependent_classes, blob)

        # Used fields from external dependencies
        ClassParser.get_method_f_deps(function_node, class_identifier, class_imports, static_imports, metadata, var_declars, dependent_classes, blob)
        metadata.pop('static_methods_used')

        #Modifiers and Return Value
        for child in function_node.children:
            if child.type == "modifiers":
                metadata['modifiers']  = ' '.join(ClassParser.match_from_span(child, blob).split())
                for modifier_child in child.children:
                    if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                        #line_comment_str = ClassParser.match_from_span(modifier_child, blob)
                        line_comment_str = modifier_child.text.decode("utf-8")
                        #line_comment_to_block = line_comment_str
                        #line_comment_to_block = line_comment_to_block.replace("//", "").strip()
                        #line_comment_to_block = "/* " + line_comment_to_block + " */"
                        #print("\n\n")
                        #print(f"Comment in method modifier {metadata['modifiers']} => {line_comment_str}")
                        #print("\n\n")
                        metadata['modifiers'] = metadata['modifiers'].replace(line_comment_str, "").strip()
            
            if child.type == "type_parameters":
                metadata['type_parameters'] = ClassParser.match_from_span(child, blob)
            
            #if "type" in child.type and child.type != "type_parameters":
            if "type" in child.type: # void_type, boolean_type, integral_type, type_identifier, etc.
                metadata['return'] = ClassParser.match_from_span(child, blob)
        
        #Signature
        format_signature = '{}{}{}{}' if metadata['is_constructor'] == True else ('{}{} {}{}' if metadata['type_parameters'] == "" else '{} {} {}{}')
        format_full_signature = '{}{} {}{}{}' if metadata['is_constructor'] == True else ('{}{} {} {}{}' if metadata['type_parameters'] == "" else '{} {} {} {}{}')
        format_full_signature_parameters = '{}{} {}{}' if metadata['is_constructor'] == True else ('{}{} {} {}' if metadata['type_parameters'] == "" else '{} {} {} {}')
        
        metadata['signature'] = format_signature.format(metadata['type_parameters'], metadata['return'], metadata['method_name'], full_parameters_str).strip()
        metadata['full_signature'] = format_full_signature.format(metadata['modifiers'], metadata['type_parameters'], metadata['return'], metadata['method_name'], full_parameters_str).strip()
        metadata['full_signature_parameters'] = format_full_signature_parameters.format(metadata['modifiers'], metadata['type_parameters'], metadata['return'], metadata['parameters']).strip()

        metadata['class_method_signature'] = '{}.{}{}'.format(class_identifier, metadata['method_name'], full_parameters_str).strip()


        # Reorganize method invocations:
        undefined_method_dependencies = set()
        explicit_dependencies = set()
        not_explicit_dependencies = list()
        #print("\n\n\nDependencies: ")
        #print(metadata['class_method_signature'])
        #print(metadata['used_external_dependencies'])
        #print(metadata['method_dependencies_by_class'])
        for dependency in metadata['used_external_dependencies']:
            #try:
            if (("." in dependency and dependency not in dependent_classes)
                    or len(dependency.strip()) == 0 # Possibly caused by encoding error
                    #or dependency[0].islower() 
                    or dependency.islower() 
                    or dependency in static_imports): # Not explicit dependency
                not_explicit_dependencies.append(dependency)
                undefined_method_dependencies.update(metadata['method_dependencies_by_class'][dependency])
                metadata['method_dependencies_by_class'].pop(dependency)
            else:
                explicit_dependencies.add(dependency)
            #except Exception as ex:
            #    print(f"\n\n\n\n Dependency error: '{dependency}'  \n\n\n\n")
            #    raise ex
        
        for dependency in metadata['field_dependencies_by_class']:
            explicit_dependencies.add(dependency)
        
        for dependency in metadata['method_references_dependencies_by_class']:
            explicit_dependencies.add(dependency)

        for dependency in dependent_classes:
            if dependency in JAVA_LANG_CLASSES_TYPES:
                continue
            explicit_dependencies.add(dependency)
        
        # Get only methods from explicit_dependencies
        methods_from_explicit_dependencies = set()
        methods_from_not_explicit_dependencies = set()
        for method in metadata['external_method_dependencies']:
            if ClassParser.method_is_from_not_explicit_dependencies(method, not_explicit_dependencies):
                methods_from_not_explicit_dependencies.add(method)
            else:
                methods_from_explicit_dependencies.add(method)
        
        metadata['used_external_dependencies'] = sorted(list(explicit_dependencies))
        metadata['methods_from_external_dependencies'] = sorted(list(methods_from_explicit_dependencies))
        metadata['undefined_method_dependencies'] = sorted(list(undefined_method_dependencies))

        metadata.pop('external_method_dependencies') # remove innecesary key
        #metadata.pop('used_external_dependencies') # remove innecesary key

        #metadata['used_not_explicit_external_dependencies'] = not_explicit_dependencies
        #metadata['methods_from_not_explicit_dependencies'] = list(methods_from_not_explicit_dependencies)

        if metadata['is_testcase'] == True:
            metadata['test_use_mockito'] = ClassParser.test_use_mockito(metadata, fields_using_mockito_annotations)

        return metadata
    

    @staticmethod
    def method_is_from_not_explicit_dependencies(method: str, not_explicit_dependencies: list):
        for dependency in not_explicit_dependencies:
            if method.startswith(dependency):
                return True
        
        return False


    @staticmethod
    def test_use_mockito(metadata, fields_using_mockito_annotations: list):
        for used_fiel in metadata['class_fields_used']:
            if used_fiel in fields_using_mockito_annotations:
                return True

        for external_dependency in metadata['used_external_dependencies']:
            if external_dependency in MOCKITO_CLASSES:
                return True
        
        for mockito_method in MOCKITO_METHODS:
            _mockito_method = MOCKITO_METHODS[mockito_method] + "." + mockito_method
            if _mockito_method in metadata['methods_from_external_dependencies']:
                return True

        return False


    @staticmethod
    def get_method_name_and_params(function_node, metadata, blob: str):
        '''
        Get focal method name and parameters
        :param function_node:
        :param blob: full context
        :return: dependent classes in parameters, variavles to ClassTypes
        '''
        declarators = []
        ClassParser.traverse_type(function_node, declarators, '{}_declaration'.format(function_node.type.split('_')[0]))
        parameters_types = []
        full_parameter_list = []
        dependent_classes = []
        instance_2_classes = {}
        for n in declarators[0].children:
            if n.type == 'identifier':
                metadata['method_name'] = ClassParser.match_from_span(n, blob).strip('(')
            elif n.type == 'formal_parameters':
                full_parameter_list.append(ClassParser.match_from_span(n, blob).strip())
                parameters_types, d_classes, inst_2_classes = ClassParser.parse_parameters(n, blob)
                dependent_classes.extend(d_classes)
                instance_2_classes.update(inst_2_classes)
        
        #metadata['parameters'] = ' '.join(full_parameter_list)
        metadata['parameters'] = metadata['method_name'] + '(' + ', '.join(parameters_types) + ')'
        metadata['parameters_list'] = parameters_types
        return full_parameter_list, dependent_classes, instance_2_classes
    

    @staticmethod
    def parse_parameters(param_node, blob: str):
        """
        Get parameter's type, classes, instance&type lists
        in the focal method's parameters.
        """
        param_list = []
        d_class_list = []
        instance2Class = {}
        #print("\n\nAll Params: " + str(param_node.text.decode("utf-8")))
        for child in param_node.named_children: # Iterate each formal_parameter and spread_parameter (por ejemplo, Integer... values)
            #print("\nParam: " + str(child))
            #print("Param text: " + str(child.text.decode("utf-8")))

            if child.type == "block_comment" or child.type == "line_comment":
                #print("Omitimos comment")
                continue

            class_index = 0
            instance_index = 1
            #print(child.named_children[class_index])
            if child.named_children[0].type == 'modifiers':  # Si el parámetro tiene modificadores, los omitimos
                # Por ejemplo @Nullable final
                #class_index += 1
                #instance_index += 1
                class_index = 1
                instance_index = 2

            # class_name = ClassParser.match_from_span(child.child_by_field_name('type'), blob)
            #first_element = ClassParser.match_from_span(child.named_children[0], blob)
            #if ('final' in first_element):
            #    #or '@' in first_element):
            #    class_index = 1
            #    instance_index = 2
            
            dimensions_node = child.child_by_field_name('dimensions')

            class_name = ClassParser.match_from_span(child.named_children[class_index], blob)
            #print("Class_name: " + str(class_name))
            if dimensions_node is not None:
                class_name = class_name + "[]"
            
            if not class_name.islower():  # class type
                class_name = class_name.replace(" ", "")
                d_class_list.append(class_name.split("[")[0])

            param_list.append(class_name)
            class_instance = ClassParser.match_from_span(child.named_children[instance_index], blob)
            instance2Class[class_instance] = class_name

        return param_list, d_class_list, instance2Class
    

    @staticmethod
    def get_field_dependencies(dependent_classes, instance_2_classes, fields):
        for f in fields:
            instance_2_classes['this.' + f['var_name']] = f['type']
            
            field_type = f['type']
            field_type = field_type.split("[")[0]
            if field_type not in dependent_classes:
                dependent_classes.append(field_type)
        return dependent_classes, instance_2_classes
    

    @staticmethod
    def get_dependencies_from_object_creation(function_node, dependent_classes: list, blob: str):
        object_creation_nodes = []
        ClassParser.traverse_type(function_node, object_creation_nodes, "object_creation_expression")
        for obj_creation_node in object_creation_nodes:
            obj_creation_type_node = obj_creation_node.child_by_field_name('type')
            obj_creation_class_name = ClassParser.match_from_span(obj_creation_type_node, blob)

            if obj_creation_class_name not in dependent_classes:
                dependent_classes.append(obj_creation_class_name)


        array_creation_nodes = []
        ClassParser.traverse_type(function_node, array_creation_nodes, "array_creation_expression")
        for arr_creation_node in array_creation_nodes:
            arr_creation_type_node = arr_creation_node.child_by_field_name('type')
            arr_creation_class_name = ClassParser.match_from_span(arr_creation_type_node, blob)

            if arr_creation_class_name not in dependent_classes:
                dependent_classes.append(arr_creation_class_name)

        return dependent_classes


    @staticmethod
    def get_used_static_imports(function_body_node, static_imports, blob: str) -> List:
        used_static_imports = set()

        id_list = []
        ClassParser.traverse_type(function_body_node, id_list, 'identifier')
        
        for id_node in id_list:
            id = ClassParser.match_from_span(id_node, blob)
            if id in static_imports:
                used_static_imports.add(id)

        return list(used_static_imports)


    @staticmethod
    def is_getter_or_setter(function_node, fields, parameters_list):
        '''
        Is this method a getter or setter.
        '''
        fields_name = [f['var_name'] for f in fields]

        exp_statements = []
        ClassParser.traverse_type(function_node, exp_statements, 'expression_statement')

        local_declarations = []
        ClassParser.traverse_type(function_node, local_declarations, 'local_variable_declaration')

        ret_statements = []
        ClassParser.traverse_type(function_node, ret_statements, 'return_statement')

        ass_statements = []
        ClassParser.traverse_type(function_node, ass_statements, 'assignment_expression')
        
        # check setter
        count_setters = 0
        set_field_class = False
        for ass_statement in ass_statements:
            #print()
            #print("statement: " + statement.text.decode().lstrip("b'"))
            for child in ass_statement.children:
                #print("\nchild: " + str(child))
                access_using_this = False
                instance = ""
                for _child in child.children:
                    #print("_child: " + str(_child))
                    if _child.type == 'this':
                        access_using_this = True
                    if _child.type == 'identifier':
                        instance = _child.text.decode().lstrip("b'")
                
                if (access_using_this == True 
                    or (access_using_this == True and instance in fields_name)):
                    set_field_class = True

                if child.type == "field_access" and (child.next_sibling is not None) and child.next_sibling.type == "=" and len(parameters_list) == 1:
                    count_setters += 1
                    #return True

        if (set_field_class == True 
                and count_setters == 1 
                and len(ret_statements) == 0
                and len(local_declarations) == 0):
            return True
        
        # check getter
        get_field_class = False
        for ret_statement in ret_statements:
            for child in ret_statement.children:
                if child.type == "return":
                    ret_val = child.next_named_sibling
                    if (ret_val is not None) and (ret_val.text.decode().lstrip("b'") in fields_name) and (len(parameters_list) == 0):
                        get_field_class = True
                        #return True
        
        if (get_field_class == True
                and len(exp_statements) == 0
                and len(local_declarations) == 0):
            return True

        return False
    

    @staticmethod
    def use_fields(function_body_node, metadata, class_fields, blob: str):
        '''
        If the method use any fields of the class.
        '''
        if function_body_node is None:  # this function has no block
            return False
        
        used_fields = set()
        fields_name = [f['var_name'] for f in class_fields]
        body_use_fields = False

        fields_access = []
        ClassParser.traverse_type(function_body_node, fields_access, "field_access")
        #ClassParser.traverse_type(function_body_node, fields_access_node, "object_creation_expression")
        #if len(fields_access) != 0:
        for field_access_node in fields_access:
            access_using_this = False
            instance = ""
            for child in field_access_node.children:
                if child.type == 'this':
                    access_using_this = True
                
                if child.type == 'identifier':
                    instance = ClassParser.match_from_span(child, blob)
            
            if access_using_this == True and instance in fields_name:
                used_fields.add(instance)
                body_use_fields = True
        
        
        id_list = []
        ClassParser.traverse_type(function_body_node, id_list, 'identifier')
        
        for id_node in id_list:
            id = ClassParser.match_from_span(id_node, blob)
            if id in fields_name:
                used_fields.add(id)
                body_use_fields = True
        
        metadata['class_fields_used'] = list(used_fields)
        return body_use_fields


    @staticmethod
    def get_method_m_deps(function_node, class_name: str, static_imports, metadata, var_declars: dict, dependent_classes: list, instance_2_classes: dict, fields, blob: str):
        '''
        Get method dependencies of focal method.
        :param dependent_classes: dependent classes of the focal method
        :param instance_2_classes: variable to Class type (or primary type)
        '''
        
        #print("\n\n\nVar declars = " + str(var_declars))
        #print("\ninstance_2_classes = " + str(instance_2_classes))
        #print("\ndependent_classes = " + str(dependent_classes))
        #print("\nstatic_imports = " + str(static_imports))

        fields_name = [f['var_name'] for f in fields]

        class_methods_that_invoke_other_methods = {}

        invocation = []
        used_external_dependencies = set()
        #method_invocations = list()
        obj2method_invocations = {}
        external_invocations = list()
        static_methods_used = list()
        ClassParser.traverse_type(function_node, invocation, '{}_invocation'.format(function_node.type.split('_')[0]))
        for inv in invocation:
            #complete_exp = ClassParser.match_from_span(inv, blob)
            #print(f"\nComplete expresion: {str(complete_exp)}")

            name = inv.child_by_field_name('name')
            method_invocation = ClassParser.match_from_span(name, blob)
            #method_invocations.append(method_invocation)

            obj = inv.child_by_field_name('object')
            args = inv.child_by_field_name('arguments')
            method_inv_args_type = ClassParser.get_inv_arg_type(var_declars, dependent_classes, args, blob)
            #print(f"Arguments list: " + str(method_inv_args_type))
            method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'

            if obj is not None:
                obj_instance = ClassParser.match_from_span(obj, blob)

                #print("obj_instance = " + str(obj_instance))
                #print("obj node = " + str(obj))

                if obj.type == 'method_invocation': # Por ejemplo, new MyClass().methodCaller().methodInvocated()
                    method_invoc_object_node = obj.child_by_field_name('object')
                    method_invoc_name_node = obj.child_by_field_name('name')
                    method_invoc_args_node = obj.child_by_field_name('arguments')

                    #print("method_invoc_object_node = " + str(method_invoc_object_node))
                    #print("")
                    
                    if (method_invoc_object_node is not None 
                            and method_invoc_object_node.type == 'object_creation_expression'):
                        type_object = method_invoc_object_node.child_by_field_name('type')
                        type_object_name = ClassParser.match_from_span(type_object, blob)

                        if (type_object_name == class_name):
                            method_invoc_name_caller = ClassParser.match_from_span(method_invoc_name_node, blob)
                            method_inv_args_type_caller = ClassParser.get_inv_arg_type(var_declars, dependent_classes, method_invoc_args_node, blob)

                            method_brief_sig_called = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                            method_brief_sig_caller = method_invoc_name_caller + '(' + ', '.join(method_inv_args_type_caller) + ')'

                            #print("\n\nMethod caller: " + method_brief_sig_caller)
                            #print("Method called: " + method_brief_sig_called)
                            #print()

                            if method_brief_sig_caller not in class_methods_that_invoke_other_methods:
                                class_methods_that_invoke_other_methods.setdefault(method_brief_sig_caller, {})
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['method_name_caller'] = method_invoc_name_caller
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['parameters_list_caller'] = method_inv_args_type_caller
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['methods_invocated'] = {}
                            
                            if method_brief_sig_called not in class_methods_that_invoke_other_methods[method_brief_sig_caller]['methods_invocated']:
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['methods_invocated'].setdefault(method_brief_sig_called, {})
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['methods_invocated'][method_brief_sig_called]['method_name_invocated'] = method_invocation
                                class_methods_that_invoke_other_methods[method_brief_sig_caller]['methods_invocated'][method_brief_sig_called]['parameters_list_invocated'] = method_inv_args_type

                            continue
                

                if obj.type == 'field_access': # Por ejemplo, new MyClass().someField.someMethod()
                    field_access_object_node = obj.child_by_field_name('object')
                    field_access_field_node = obj.child_by_field_name('field')
                    invoc_field_name = ClassParser.match_from_span(field_access_field_node, blob)

                    #if field_access_object_node.type == 'this':
                    #    if (invoc_field_name in fields_name 
                    #            and invoc_field_name in var_declars):
                    #        print()

                    if field_access_object_node.type == 'object_creation_expression':
                        type_object = field_access_object_node.child_by_field_name('type')
                        type_object_name = ClassParser.match_from_span(type_object, blob)

                        if (type_object_name == class_name 
                                and invoc_field_name in fields_name 
                                and 'this.' + invoc_field_name in var_declars): # Se llama desde un field de la clase
                            #print(f"\nVar inner name = {type_object_name}.{invoc_field_name}")
                            dependency_name = var_declars['this.' + invoc_field_name]
                            dependency_name = dependency_name.split("[")[0]

                            if dependency_name in JAVA_LANG_CLASSES_TYPES:
                                continue

                            #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'

                            used_external_dependencies.add(dependency_name)
                            external_invocations.append(dependency_name + '.' + method_brief_sig)

                            ClassParser.set_method_dependency(obj2method_invocations, dependency_name, method_brief_sig, method_invocation, method_inv_args_type)
                            
                            continue


                if obj.type == 'object_creation_expression': # Por ejemplo: new SomeClass().methodInvocation()
                    creation_expression_type_node = obj.child_by_field_name('type')
                    creation_expression_class_name = ClassParser.match_from_span(creation_expression_type_node, blob)

                    if creation_expression_class_name in JAVA_LANG_CLASSES_TYPES:
                        continue
                    
                    #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                    
                    if creation_expression_class_name == class_name:
                        ClassParser.set_method_dependency(obj2method_invocations, 'this', method_brief_sig, method_invocation, method_inv_args_type)

                    else:
                        used_external_dependencies.add(creation_expression_class_name)
                        external_invocations.append(creation_expression_class_name + '.' + method_brief_sig)

                        ClassParser.set_method_dependency(obj2method_invocations, creation_expression_class_name, method_brief_sig, method_invocation, method_inv_args_type)

                    continue


                if obj_instance not in instance_2_classes: # El método no se llama desde una variable declarada (local o global)
                    if obj_instance == 'this' or obj_instance == 'super' or obj_instance == class_name:
                        # El método se llama usando this o super, ó es un método estático de la clase
                        # que se llama usando MyClass.methodInvocation()
                        #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                        ClassParser.set_method_dependency(obj2method_invocations, 'this', method_brief_sig, method_invocation, method_inv_args_type)
                        continue

                    dependency_name = ""
                    #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'

                    if (obj_instance not in var_declars # No es una variable local o parámetro de método
                            and 'this.' + obj_instance in var_declars): # Sino que es una variable de la clase
                        obj_instance = 'this.' + obj_instance

                    if obj_instance in var_declars:
                        # Por ejemplo variables declaradas dentro del método
                        #print("Call from var_declars: " + complete_exp)
                        dependency_name = var_declars[obj_instance]
                        invocation_from_not_explicit_variable = dependency_name + '.' + method_brief_sig

                    elif obj.type == "array_access": # Por ejemplo: someArray[0].someMethod()
                        obj_array = obj.child_by_field_name('array')
                        obj_array_instance = ClassParser.match_from_span(obj_array, blob)
                        if (obj_array_instance not in var_declars # No es una variable local o parámetro de método
                                and 'this.' + obj_array_instance in var_declars): # Sino que es una variable de la clase
                            obj_array_instance = 'this.' + obj_array_instance

                        if obj_array_instance in var_declars:
                            dependency_name = var_declars[obj_array_instance]
                            dependency_name = dependency_name.split("[")[0]
                            invocation_from_not_explicit_variable = dependency_name + '.' + method_brief_sig
                        else:
                            dependency_name = obj_instance
                            invocation_from_not_explicit_variable = dependency_name + '.' + method_brief_sig

                    else: # Por ejemplo: new SomeClass().otherMethod().methodInvocation()
                        #print(f"\n\nNo es una dependencia explicita: {obj_instance}   ->   {complete_exp}")
                        #print("\n\n")
                        dependency_name = obj_instance
                        invocation_from_not_explicit_variable = dependency_name + '.' + method_brief_sig
                    
                    if dependency_name in JAVA_LANG_CLASSES_TYPES:
                        continue
                    
                    used_external_dependencies.add(dependency_name)
                    external_invocations.append(invocation_from_not_explicit_variable)

                    ClassParser.set_method_dependency(obj2method_invocations, dependency_name, method_brief_sig, method_invocation, method_inv_args_type)

                    continue


                obj_class = instance_2_classes[obj_instance]
                if obj_class in JAVA_LANG_CLASSES_TYPES:
                    continue

                #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'

                if obj_class == class_name:
                    ClassParser.set_method_dependency(obj2method_invocations, 'this', method_brief_sig, method_invocation, method_inv_args_type)
                    continue

                if obj_class in dependent_classes:
                    used_external_dependencies.add(obj_class)
                    external_invocations.append(obj_class + '.' + method_brief_sig)

                    ClassParser.set_method_dependency(obj2method_invocations, obj_class, method_brief_sig, method_invocation, method_inv_args_type)
                    
            else:
                if (method_invocation in static_imports 
                        and static_imports[method_invocation] not in JAVA_LANG_CLASSES_TYPES):
                    # El método es de una importación estática
                    static_class_invocator = static_imports[method_invocation]
                    used_external_dependencies.add(static_class_invocator)
                    #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                    external_invocations.append(static_class_invocator + '.' + method_brief_sig)
                    static_methods_used.append(method_invocation)

                    ClassParser.set_method_dependency(obj2method_invocations, static_class_invocator, method_brief_sig, method_invocation, method_inv_args_type)
                    
                else:
                    # El método es de la misma clase, o a una clase padre,
                    # y no se llama usando this, ni super, ni el nombre de la case (en caso de que sea estático)
                    #method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                    ClassParser.set_method_dependency(obj2method_invocations, 'this', method_brief_sig, method_invocation, method_inv_args_type)
        
        #print("\n\nClass Method Invocators: " + str(class_methods_that_invoke_other_methods))
        #metadata['invocations'] = method_invocations
        if 'this' in obj2method_invocations:
            metadata['class_methods_used'] = obj2method_invocations['this']
            obj2method_invocations.pop('this')
        metadata['method_dependencies_by_class'] = obj2method_invocations
        metadata['external_method_dependencies'] = external_invocations
        metadata['used_external_dependencies'] = sorted(list(used_external_dependencies))
        metadata['class_methods_that_invoke_other_methods'] = class_methods_that_invoke_other_methods
        metadata['static_methods_used'] = static_methods_used
    

    @staticmethod
    def set_method_dependency(obj2method_invocations: dict, dependency_class_name: str, method_brief_sig: str, method_invocation: str, method_inv_args_type: list):
        obj2method_invocations.setdefault(dependency_class_name, {})
        if method_brief_sig not in obj2method_invocations[dependency_class_name]:
            obj2method_invocations[dependency_class_name].setdefault(method_brief_sig, {})
            obj2method_invocations[dependency_class_name][method_brief_sig]['method_name'] = method_invocation
            obj2method_invocations[dependency_class_name][method_brief_sig]['parameters_list'] = method_inv_args_type


    @staticmethod
    def get_method_m_refs_deps(function_node, class_name: str, class_imports: list, metadata, var_declars: dict, dependent_classes: list, blob: str):
        '''
        Get method dependencies of focal method.
        :param dependent_classes: dependent classes of the focal method
        :param instance_2_classes: variable to Class type (or primary type)
        '''

        method_references = []
        ClassParser.traverse_type(function_node, method_references, 'method_reference')

        obj2methodref_invocations = {}
        method_references_from_external_dependencies = set()

        for m_ref in method_references:
            #print("\n\n\nm_ref = " + str(m_ref))

            for child in m_ref.children:
                #print("\nchild_node = " + str(child))
                if child.type == 'array_type': # Por ejemplo, SomeClass[]::new
                    break

                if child.type == 'field_access': # Por ejemplo, System.out::println o this.somObj::someMethod
                    object_node = child.child_by_field_name('object')
                    object_access = ClassParser.match_from_span(object_node, blob)

                    if object_access == 'this':
                        field_node = child.child_by_field_name('field')
                        reference_name = ClassParser.match_from_span(field_node, blob)
                        reference_name = 'this.' + reference_name
                        #print("\n\nreference_name = " + str(reference_name))

                        method_node = child.next_named_sibling

                        if method_node is None:
                            break
                    
                        method_name = ClassParser.match_from_span(method_node, blob)
                        #print("method_name = " + str(method_name))
                        
                        if (reference_name in var_declars and var_declars[reference_name] == class_name):
                            if method_name not in metadata['class_method_references_used']:
                                metadata['class_method_references_used'].append(method_name)
                            break

                        if (reference_name not in var_declars):
                            break

                        dependency_type = var_declars[reference_name]
                        dependency_type = dependency_type.split("[")[0]
                        if dependency_type in JAVA_LANG_CLASSES_TYPES:
                            break

                        method_references_from_external_dependencies.add(dependency_type + "::" + method_name)

                        obj2methodref_invocations.setdefault(dependency_type, [])
                        if method_name not in obj2methodref_invocations[dependency_type]:
                            obj2methodref_invocations[dependency_type].append(method_name)

                    break

                if child.type == 'identifier':
                    reference_name = ClassParser.match_from_span(child, blob)
                    #print("reference_name = " + str(reference_name))

                    # SomeClass::someMethod or someVar::someMethod
                    method_node = child.next_named_sibling
                    #print("method_node = " + str(method_node))

                    if method_node is None: # Por ejemplo, SomeClass::new
                        break

                    method_name = ClassParser.match_from_span(method_node, blob)
                    #print("method_name = " + str(method_name))

                    if (reference_name not in var_declars # No es una variable local o parámetro de método
                            and 'this.' + reference_name in var_declars): # Sino que es una variable de la clase
                        reference_name = 'this.' + reference_name

                    if ((reference_name in var_declars and var_declars[reference_name] == class_name)
                            or reference_name == class_name):
                        if method_name not in metadata['class_method_references_used']:
                            metadata['class_method_references_used'].append(method_name)
                        break

                    if (reference_name not in var_declars 
                            and reference_name not in class_imports 
                            and reference_name not in dependent_classes):
                        break

                    dependency_type = reference_name if (reference_name in class_imports or reference_name in dependent_classes) else var_declars[reference_name]
                    dependency_type = dependency_type.split("[")[0]
                    if dependency_type in JAVA_LANG_CLASSES_TYPES:
                        break

                    #if dependency_type not in metadata['used_external_dependencies']:
                    #    metadata['used_external_dependencies'].append(dependency_type)
                    
                    method_references_from_external_dependencies.add(dependency_type + "::" + method_name)

                    obj2methodref_invocations.setdefault(dependency_type, [])
                    if method_name not in obj2methodref_invocations[dependency_type]:
                        obj2methodref_invocations[dependency_type].append(method_name)
                    
                    break
        
        metadata['method_references_dependencies_by_class'] = obj2methodref_invocations
        metadata['method_references_from_external_dependencies'] = sorted(list(method_references_from_external_dependencies))
        

    @staticmethod
    def get_method_f_deps(function_node, class_name, class_imports: list, static_imports: dict, metadata, var_declars: dict, dependent_classes: list, blob: str):
        '''
        Get field dependencies of focal method.
        :param dependent_classes: dependent classes of the focal method
        :param instance_2_classes: variaBle to Class type (or primary type)
        '''
        static_methods_used = metadata['static_methods_used']

        fields_access = []
        ClassParser.traverse_type(function_node, fields_access, 'field_access')

        obj2field_invocations = {}
        fields_from_external_dependencies = set()

        for field_access_node in fields_access:
            access_using_creation_exp = False
            object_node = field_access_node.child_by_field_name('object')
            object_assign = ClassParser.match_from_span(object_node, blob)

            field_node = field_access_node.child_by_field_name('field')
            field_assign = ClassParser.match_from_span(field_node, blob)

            if (object_assign == 'this' 
                    or object_assign == 'super'):
                # Cases this.someField -> Omitimos porque son fields de la clase
                continue

            # Se accede al field usando someArray[0].someField
            if object_node.type == 'array_access':
                obj_array = object_node.child_by_field_name('array')
                object_assign = ClassParser.match_from_span(obj_array, blob)
            
            # Se accede al field usando new SomeClass().someFiled
            if object_node.type == 'object_creation_expression':
                obj_new_instance = object_node.child_by_field_name('type')
                object_assign = ClassParser.match_from_span(obj_new_instance, blob)
                access_using_creation_exp = True

            #print("\nObject: " + object_assign)
            #print("Field: " + field_assign)

            for child in field_access_node.children:
                if child.type == 'field_access': # Cases this.someField.someAttr or someObject.someValue.someAttr
                    _object_node = child.child_by_field_name('object')
                    _object_assign = ClassParser.match_from_span(_object_node, blob)

                    _field_node = child.child_by_field_name('field')
                    _field_assign = ClassParser.match_from_span(_field_node, blob)

                    if _object_assign != 'this':
                        # Cases someObject.someValue.someAttr ->
                        # Omitimos porque son fields de dependencias asociadas a otras dependencias
                        # Y por ende no podemos saber el tipo de dato de la dependencia padre del field
                        break

                    #print("Object Child: " + _object_assign)
                    #print("Field Child: " + _field_assign)

                    object_assign = 'this.' + _field_assign
                    continue
            

            if ('this.' not in object_assign # No se accede usando this.obj.someField, sino obj.someField
                    and object_assign not in var_declars # No es una variable local o parámetro de método
                    and 'this.' + object_assign in var_declars): # Sino que es una variable de la clase
                object_assign = 'this.' + object_assign


            if ((object_assign in var_declars and var_declars[object_assign] == class_name)
                    or (access_using_creation_exp == True and object_assign == class_name)
                    or object_assign == class_name):
                # Se accede al field a través de una variable que es del mismo tipo de la clase
                # ó se accede vía new MyClass().someField
                # ó es de tipo estático y se accede vía MyClass.SOME_FIELD
                if field_assign not in metadata['class_fields_used']:
                    metadata['class_fields_used'].append(field_assign)
                continue

            if (object_assign not in var_declars 
                    and object_assign not in class_imports # En caso de que sea un field estático de otra clase (SomeClass.STATIC_FIELD)
                    and object_assign not in dependent_classes 
                    and access_using_creation_exp == False):
                # En caso de que el valor no esté dentro de var_declars,
                # Omitimos porque no podemos obtener la clase a la que pertenece el field
                continue

            #print("Object asignado: " + object_assign)
            #print("Field asignado:  " + field_assign)

            dependency_type = object_assign if (object_assign in class_imports or object_assign in dependent_classes or access_using_creation_exp == True) else var_declars[object_assign]
            dependency_type = dependency_type.split("[")[0]
            if dependency_type in JAVA_LANG_CLASSES_TYPES:
                continue
            
            fields_from_external_dependencies.add(dependency_type + "." + field_assign)

            obj2field_invocations.setdefault(dependency_type, [])
            if field_assign not in obj2field_invocations[dependency_type]:
                obj2field_invocations[dependency_type].append(field_assign)
        
        id_list = []
        ClassParser.traverse_type(function_node, id_list, 'identifier')
        
        for id_node in id_list:
            id = ClassParser.match_from_span(id_node, blob)
            if id in static_imports and id not in static_methods_used:
                dependency_type = static_imports[id]
                fields_from_external_dependencies.add(dependency_type + "." + id)

                obj2field_invocations.setdefault(dependency_type, [])
                if id not in obj2field_invocations[dependency_type]:
                    obj2field_invocations[dependency_type].append(id)
        
        metadata['field_dependencies_by_class'] = obj2field_invocations
        metadata['fields_from_external_dependencies'] = sorted(list(fields_from_external_dependencies))
        #print("\nField invocations = " + str(obj2field_invocations))


    @staticmethod
    def get_var_declar(function_node, param_var_declars, blob: str):
        '''
        Get all variable declarations in this body and method's parameters.
        :param param_var_declars: variables and thier types in method's parameters
        '''
        var_declars = {}
        var_declars.update(param_var_declars)
        declar_nodes = []
        ClassParser.traverse_type(function_node, declar_nodes, 'local_variable_declaration')
        for dn in declar_nodes:
            #print(str(dn))
            for child in dn.children:
                #print(str(child))
                if (child.type == 'type_identifier' # por ejemplo, SomeClass variable; # también reconoce 'scoped_type_identifier' (por ejemplo Map.Entry)
                        or child.type == 'integral_type' # por ejemplo, int, long, byte, short, char
                        or child.type == 'floating_point_type' # por ejemplo, float, double
                        or child.type == 'boolean_type'): 
                    dtype = ClassParser.match_from_span(child, blob)
                    if dtype == 'var': # Java 11+
                        # No agregamos ya que con 'var' no podemos saber el tipo de dato declarado
                        break
                    #print(f"type_identifier dtype: {dtype}")
                    var_node = child.next_named_sibling
                    if var_node.type == 'variable_declarator':
                        for _child in var_node.children:
                            if _child.type == 'identifier':
                                dvar = ClassParser.match_from_span(_child, blob)
                                var_declars[dvar] = dtype.replace(" ", "")
                                break
                
                elif child.type == 'array_type': # por ejemplo, SomeClass[] var;
                    dtype = ClassParser.match_from_span(child, blob)

                    var_node = child.next_named_sibling
                    if var_node.type == 'variable_declarator':
                        for _child in var_node.children:
                            if _child.type == 'identifier':
                                dvar = ClassParser.match_from_span(_child, blob)
                                var_declars[dvar] = dtype.replace(" ", "")
                                break

                elif child.type == 'generic_type': # por ejemplo, SomeClass<?> var;
                    dtype = ClassParser.match_from_span(child, blob)
                    #for _c in child.children:
                    #    if _c.type == 'type_identifier':
                    #        dtype = ClassParser.match_from_span(_c, blob)
                    #        break
                    
                    #print(f"generic_type dtype: {dtype}")
                    var_node = child.next_named_sibling
                    if var_node.type == 'variable_declarator':
                        for _child in var_node.children:
                            if _child.type == 'identifier':
                                dvar = ClassParser.match_from_span(_child, blob)
                                var_declars[dvar] = dtype.replace(" ", "")
                                break
        
        
        try_with_resource_statements_nodes = [] # Por ejemplo: try (Writer w = new Writer())
        ClassParser.traverse_type(function_node, try_with_resource_statements_nodes, 'try_with_resources_statement')

        #print(var_declars)

        for res_statement_node in try_with_resource_statements_nodes:
            resources_node = res_statement_node.child_by_field_name('resources')

            for res_node in resources_node.children:
                if res_node.type == 'resource':
                    res_node_text = ClassParser.match_from_span(res_node, blob)
                    #print(res_node_text)
                    if res_node_text in var_declars or 'this.' + res_node_text in var_declars:
                        # Por ejemplo:
                        # ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                        # try (bytes) {}
                        continue

                    type_node = res_node.child_by_field_name('type')
                    if type_node is None:
                        continue
                    type_class_name = ClassParser.match_from_span(type_node, blob)

                    var_node = res_node.child_by_field_name('name')
                    var_name = ClassParser.match_from_span(var_node, blob)

                    var_declars[var_name] = type_class_name.replace(" ", "")
        

        enhanced_for_statement_nodes = [] # Por ejemplo: for (Type t : list)
        ClassParser.traverse_type(function_node, enhanced_for_statement_nodes, 'enhanced_for_statement')

        for foreach_stm_node in enhanced_for_statement_nodes:
            type_node = foreach_stm_node.child_by_field_name('type')
            type_class_name = ClassParser.match_from_span(type_node, blob)

            var_node = foreach_stm_node.child_by_field_name('name')
            var_name = ClassParser.match_from_span(var_node, blob)

            var_declars[var_name] = type_class_name.replace(" ", "")


        #print(f"var_declars: {str(var_declars)}")
        return var_declars
    

    @staticmethod
    def get_invocations_into_statements(function_node, other_var_declars, blob: str):
        '''
        Get all variable declarations in this body and method's parameters.
        :param param_var_declars: variables and thier types in method's parameters
        '''
        var_declars = {}
        var_declars.update(other_var_declars)
        declar_nodes = []
        ClassParser.traverse_type(function_node, declar_nodes, 'expression_statement')
        for dn in declar_nodes:
            #print(str(dn))
            for child in dn.children:
                #print("Child invoc 1: " + str(child))
                if child.type == 'method_invocation':
                    for _child in child.children:
                        if _child.type == 'method_invocation': # Example: new SomeClass().callMethod()
                            #print("Child invoc 2: " + str(_child))
                            #expression = ClassParser.match_from_span(_child, blob)
                            #print(f"type_identifier dtype: {expression}")

                            for c in _child.children:
                                #print("Child invoc 3: " + str(c))
                                if c.type == 'object_creation_expression':
                                    dvar = ClassParser.match_from_span(c, blob)
                                    #print("dvar: " + dvar)
                                    # get type_identifier
                                    for _c in c.children:
                                        #print("Child invoc 4: " + str(_c))
                                        if _c.type == 'type_identifier':
                                            dtype = ClassParser.match_from_span(_c, blob)
                                            #print("dtype: " + dtype)
                                            var_declars[dvar] = dtype
                                            break
                                        # argument_list of constructor instance? 
                
        #print(f"invocations_into_statements: {str(var_declars)}")
        return var_declars


    @staticmethod
    def get_static_imports(import_list) -> Dict:
        static_imports = {}
        for _import in import_list:
            _imp = _import.replace(";", "")
            _imp = _imp.strip()
            if _imp.startswith("import static "):
                _imp = _imp.replace("import static ", "")
                packs = _imp.split(".")
                length_packs = len(packs)
                if length_packs > 1:
                    name_static = packs[length_packs - 1]
                    name_class = packs[length_packs - 2]
                    static_imports[name_static] = name_class

        #print(f"static_imports: {str(static_imports)}")
        return static_imports
    

    @staticmethod
    def get_class_imports(import_list) -> List:
        class_imports = list()
        for _import in import_list:
            _imp = _import.replace(";", "")
            _imp = _imp.strip()
            if not _imp.startswith("import static "):
                packs = _imp.split(".")
                length_packs = len(packs)
                name_class = packs[length_packs - 1]
                class_imports.append(name_class)

        #print(f"class_imports: {str(class_imports)}")
        return class_imports


    @staticmethod
    def get_inv_arg_type(var_declars, dependent_classes, arg_list, blob: str):
        '''
        Get argument types of an invocation in focal method body.
        :param var_declars: declared variavles in body.
        :param arg_list: argument list of the invocation.
        '''
        type_list = []
        for arg_node in arg_list.named_children:
            if arg_node.type == 'class_literal':
                #type_list.append("Class")
                arg_type_node = arg_node.named_children[0]
                if arg_type_node.type == 'type_identifier':
                    arg_type_class_name = ClassParser.match_from_span(arg_type_node, blob)
                    if arg_type_class_name.islower():
                        type_list.append("Class<?>")
                    else:
                        type_list.append("Class<" + arg_type_class_name + ">")
                else:
                    type_list.append("Class<?>")
            
            elif arg_node.type == 'string_literal':
                type_list.append("String")
            
            elif arg_node.type == 'character_literal':
                type_list.append("char")
            
            elif arg_node.type == 'true' or arg_node.type == 'false':
                type_list.append("boolean")
            
            elif arg_node.type == 'decimal_integer_literal':
                arg_type_value = ClassParser.match_from_span(arg_node, blob)
                if "L" in arg_type_value or "l" in arg_type_value:
                    type_list.append("long")
                else:
                    type_list.append("int")
            
            elif arg_node.type == 'decimal_floating_point_literal':
                arg_type_value = ClassParser.match_from_span(arg_node, blob)
                if "F" in arg_type_value or "f" in arg_type_value:
                    type_list.append("float")
                else:
                    type_list.append("double")

            elif arg_node.type == 'identifier':
                arg = ClassParser.match_from_span(arg_node, blob)
                if (arg not in var_declars # No es una variable local o parámetro de método
                        and 'this.' + arg in var_declars): # Sino que es una variable de la clase
                    arg = 'this.' + arg
                if arg in var_declars:
                    type_list.append(var_declars[arg])
                else:
                    #type_list.append(arg)
                    type_list.append("unknownType")
            
            elif arg_node.type == 'object_creation_expression':
                arg_type_node = arg_node.child_by_field_name('type')
                arg_type_class_name = ClassParser.match_from_span(arg_type_node, blob)
                if arg_type_class_name in dependent_classes:
                    type_list.append(arg_type_class_name)
                else:
                    type_list.append("unknownType")
            
            elif arg_node.type == 'array_creation_expression':
                arg_type_node = arg_node.child_by_field_name('type')
                arg_type_class_name = ClassParser.match_from_span(arg_type_node, blob)
                if arg_type_class_name in dependent_classes:
                    type_list.append(arg_type_class_name + "[]")
                else:
                    type_list.append("unknownType")
            
            elif arg_node.type == 'array_access':
                array_access_nodes = []
                ClassParser.traverse_type(arg_node, array_access_nodes, "array_access")
                find_arg_var = False
                for arr_access_node in array_access_nodes:
                    arg_var_node = arr_access_node.named_children[0]
                    if arg_var_node.type == 'identifier':
                        arg_var = ClassParser.match_from_span(arg_var_node, blob)
                        if (arg_var not in var_declars # No es una variable local o parámetro de método
                                and 'this.' + arg_var in var_declars): # Sino que es una variable de la clase
                            arg_var = 'this.' + arg_var
                        if arg_var in var_declars:
                            type_list.append(var_declars[arg_var].split("[")[0])
                            find_arg_var = True
                        break
                    if arg_var_node.type == 'field_access':
                        arg_var = ClassParser.match_from_span(arg_var_node, blob)
                        if arg_var in var_declars: # por ejemplo this.someArray
                            type_list.append(var_declars[arg_var].split("[")[0])
                            find_arg_var = True
                        break
                if find_arg_var == False:
                    type_list.append("unknownType")
            
            else: # Por ejemplo, field_access, method_invocation u otro
                type_list.append("unknownType")
        
        return type_list
    

    @staticmethod
    def traverse_type(node, results: List, kind: str) -> None:
        """
        Traverses nodes of given type and save in results
        """
        if node.type == kind:
            results.append(node)
        if not node.children:
            return
        for n in node.children:
            ClassParser.traverse_type(n, results, kind)


    @staticmethod
    def children_of_type(node, types):
        """
        Return children of node of type belonging to types

        Parameters
        ----------
        node : tree_sitter.Node
            node whose children are to be searched
        types : str/tuple
            single or tuple of node types to filter

        Return
        ------
        result : list[Node]
            list of nodes of type in types
        """
        if isinstance(types, str):
            return ClassParser.children_of_type(node, (types,))
        return [child for child in node.children if child.type in types]
    

    @staticmethod
    def get_class_full_signature(class_node, blob: str):
        """
        Extract the source code associated with a node of the tree
        """
        class_body = class_node.child_by_field_name('body')
        body_line_start = class_body.start_point[0]
        body_char_start = class_body.start_point[1]
        class_line_start = class_node.start_point[0]
        class_char_start = class_node.start_point[1]
        lines = blob.split('\n')
        if class_line_start != body_line_start:
            return '\n'.join(
                [lines[class_line_start][class_char_start:]] + lines[class_line_start + 1:body_line_start] + [
                    lines[body_line_start][:body_char_start - 1]])
        else:
            return lines[class_line_start][class_char_start:body_char_start - 1]
        

    @staticmethod
    def match_from_span(node, blob: str) -> str:
        """
        Extract the source code associated with a node of the tree
        """
        line_start = node.start_point[0]
        line_end = node.end_point[0]
        char_start = node.start_point[1]
        char_end = node.end_point[1]
        lines = blob.split('\n')
        if line_start != line_end:
            return '\n'.join([lines[line_start][char_start:]] + lines[line_start+1:line_end] + [lines[line_end][:char_end]])
        else:
            return lines[line_start][char_start:char_end]