import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from typing import List, Dict, Any, Set, Optional
from packaging import version
import pkg_resources

#from parser_utils import ParserUtils


class DependencyClassParser():

    def __init__(self, language):
        tree_sitter_version = pkg_resources.get_distribution("tree_sitter").version

        if version.parse(str(tree_sitter_version)) < version.parse("0.22.0"):
            JAVA_LANGUAGE = Language(tsjava.language(), language)
        else:
            JAVA_LANGUAGE = Language(tsjava.language())
        
        self.parser = Parser()
        self.parser.set_language(JAVA_LANGUAGE)
    

    def parse_file(self, 
                   file: str, 
                   class_name_dependency: str, 
                   external_dependency: str):
        """
        Parses a java file and extract metadata using info in method_metadata
        """

        #if ("ArrayDeque" not in file):
        #    return None

        #Build Tree
        with open(file, 'r') as content_file:
            try: 
                content = content_file.read()
                self.content = content
            except:
                return None

        #if class_name_dependency == 'ObjectConstructor':
        #    print(self.content)

        #print("\n\n\n")
        #print(file)
        #print()
        #print(content)
        #print("\n\n\n")

        tree = self.parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        has_error = root_node.has_error
        #print("\n\n\n")
        #print("HAS ERROR: " + str(has_error))
        #print("\n\n\n")
        if has_error:
            return None

        classes = [node for node in tree.root_node.children if node.type == 'class_declaration']
        interfaces = [node for node in tree.root_node.children if node.type == 'interface_declaration']
        classes.extend(interfaces)

        for _class in classes:
            class_identifier = self.match_from_span([child for child in _class.children if child.type == 'identifier'][0], content).strip()
            #print("\n\nclass_identifier = " + class_identifier)
            if class_identifier != class_name_dependency:
                continue

            class_metadata = self.get_class_metadata(_class, class_name_dependency, external_dependency, content)

            methods = list()
            
            class_metadata['has_constructor'] = False
            #Parse methods
            #for child in (child for child in _class.children if child.type == 'class_body'):
            #for child in (child for child in _class.children if child.type == 'interface_body'):
            for child in (child for child in _class.children if (child.type == 'class_body' or child.type == 'interface_body')):
                for _, node in enumerate(child.children):
                    if node.type == 'method_declaration' or node.type == 'constructor_declaration':
                        if node.type == 'constructor_declaration':
                            class_metadata['has_constructor'] = True	
                        
                        #Read Method metadata
                        method_metadata = DependencyClassParser.get_function_metadata(class_identifier, node, content)
                        methods.append(method_metadata)
            
            class_metadata['methods'] = methods

            #print("\n\n")
            #print(class_metadata)
            #print("\n\n")

            # En un file .java, solo debería haber una clase con un mismo nombre
            return class_metadata
        
        return None
    

    @staticmethod
    def get_class_metadata(class_node, class_name: str, external_dependency: str, blob: str):
        """
        Extract class-level metadata 
        """
        metadata = {
            'class_name': class_name,
            'external_dependency' : external_dependency,
            'superclass': '',
            'interfaces': '',
            'class_signature': '',
            'class_modifier': '',
            'has_constructor': '',
            'fields': '',
            'methods': '',
        }

        superclass = class_node.child_by_field_name('superclass')
        if superclass:
            metadata['superclass'] = DependencyClassParser.match_from_span(superclass, blob)
        
        interfaces = class_node.child_by_field_name('interfaces')
        if interfaces:
            metadata['interfaces'] = DependencyClassParser.match_from_span(interfaces, blob)

        metadata['class_signature'] = DependencyClassParser.get_class_full_signature(class_node, blob)

        #Modifier
        modifiers_node_list = DependencyClassParser.children_of_type(class_node, "modifiers")
        if len(modifiers_node_list) > 0:
            modifiers_node = modifiers_node_list[0]
            metadata["class_modifier"] = ' '.join(DependencyClassParser.match_from_span(modifiers_node, blob).split())
            for modifier_child in modifiers_node.children:
                if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                    #line_comment_str = DependencyClassParser.match_from_span(modifier_child, blob)
                    line_comment_str = modifier_child.text.decode("utf-8")
                    #print("\n\n")
                    #print(f"Comment in class modifier {metadata['modifiers']} => {line_comment_str}")
                    #print("\n\n")
                    metadata['class_modifier'] = metadata['class_modifier'].replace(line_comment_str, "").strip()

                    metadata['class_signature'] = metadata['class_signature'].replace(line_comment_str, "").strip()
        else:
            metadata["class_modifier"] = ""

        #Fields
        fields = DependencyClassParser.get_class_fields(class_node, blob)
        metadata['fields'] = fields

        return metadata
    

    @staticmethod
    def get_class_fields(class_node, blob: str):
        """
        Extract metadata for all the fields defined in the class
        """
        
        body_node = class_node.child_by_field_name("body")
        fields = []
        
        for f in DependencyClassParser.children_of_type(body_node, "field_declaration"):
            field_dict = {}

            #Complete field
            field_dict["original_string"] = DependencyClassParser.match_from_span(f, blob)

            #Modifier
            modifiers_node_list = DependencyClassParser.children_of_type(f, "modifiers")
            if len(modifiers_node_list) > 0:
                modifiers_node = modifiers_node_list[0]
                #field_dict["modifier"] = ClassParser.match_from_span(modifiers_node, blob)
                field_dict["modifier"] = ' '.join(DependencyClassParser.match_from_span(modifiers_node, blob).split())
                for modifier_child in modifiers_node.children:
                    if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                        #line_comment_str = DependencyClassParser.match_from_span(modifier_child, blob)
                        line_comment_str = modifier_child.text.decode("utf-8")
                        #print("\n\n")
                        #print(f"Comment in external field modifier {field_dict['modifiers']} => {line_comment_str}")
                        #print("\n\n")
                        field_dict['modifier'] = field_dict['modifier'].replace(line_comment_str, "").strip()
            else:
                field_dict["modifier"] = ""

            #Type
            type_node = f.child_by_field_name("type")
            var_type = DependencyClassParser.match_from_span(type_node, blob)
            field_dict["type"] = var_type.replace(" ", "")

            #Declarator
            declarator_node = f.child_by_field_name("declarator")
            field_dict["declarator"] = DependencyClassParser.match_from_span(declarator_node, blob)
            
            #Var name
            var_node = declarator_node.child_by_field_name("name")
            field_dict["var_name"] = DependencyClassParser.match_from_span(var_node, blob)

            fields.append(field_dict)

        return fields


    @staticmethod
    def get_function_metadata(class_identifier, 
                              function_node, 
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
            'class': '',
            'signature': '',
            'full_signature': '',
            'full_signature_parameters': '',
            'class_method_signature': '',
            'is_constructor': '',
        }

        full_parameter_list = DependencyClassParser.get_method_name_and_params(function_node, metadata, blob)
        full_parameters_str = ' '.join(full_parameter_list)

        metadata['class'] = class_identifier

        #method_body = DependencyClassParser.match_from_span(function_node, blob)
        #print("\n\n\n")
        #print(class_identifier)
        #print()
        #print(method_body)
        #print("\n\n\n")

        #Is Constructor
        metadata['is_constructor'] = False
        if function_node.type == 'constructor_declaration':
            metadata['is_constructor'] = True
        
        #Modifiers and Return Value
        for child in function_node.children:
            if child.type == "modifiers":
                metadata['modifiers']  = ' '.join(DependencyClassParser.match_from_span(child, blob).split())
                for modifier_child in child.children:
                    if modifier_child.type == "line_comment": # Por ejemplo, @SuppressWarnings("deprecation") //some comment
                        #line_comment_str = DependencyClassParser.match_from_span(modifier_child, blob)
                        line_comment_str = modifier_child.text.decode("utf-8")
                        #line_comment_to_block = line_comment_str
                        #line_comment_to_block = line_comment_to_block.replace("//", "").strip()
                        #line_comment_to_block = "/* " + line_comment_to_block + " */"
                        #print("\n\n")
                        #print(f"Comment in external method modifier {metadata['modifiers']} => {line_comment_str}")
                        #print("\n\n")
                        metadata['modifiers'] = metadata['modifiers'].replace(line_comment_str, "").strip()
                continue
            
            if child.type == "type_parameters":
                metadata['type_parameters'] = DependencyClassParser.match_from_span(child, blob)
                continue
            
            if "type" in child.type and child.type != "type_parameters":
            #if "type" in child.type: # void_type, boolean_type, integral_type, type_identifier, etc.
                metadata['return'] = DependencyClassParser.match_from_span(child, blob)
                continue
        
        #Signature
        format_signature = '{}{}{}{}' if metadata['is_constructor'] == True else ('{}{} {}{}' if metadata['type_parameters'] == "" else '{} {} {}{}')
        format_full_signature = '{} {} {}{}{}' if metadata['is_constructor'] == True and metadata['type_parameters'] != "" else ('{}{} {}{}{}' if metadata['is_constructor'] == True else ('{}{} {} {}{}' if metadata['type_parameters'] == "" else '{} {} {} {}{}'))
        format_full_signature_parameters = '{} {} {}{}' if metadata['is_constructor'] == True and metadata['type_parameters'] != "" else ('{}{} {}{}' if metadata['is_constructor'] == True else ('{}{} {} {}' if metadata['type_parameters'] == "" else '{} {} {} {}'))
        
        metadata['signature'] = format_signature.format(metadata['type_parameters'], metadata['return'], metadata['method_name'], full_parameters_str).strip()
        metadata['full_signature'] = format_full_signature.format(metadata['modifiers'], metadata['type_parameters'], metadata['return'], metadata['method_name'], full_parameters_str).strip()
        metadata['full_signature_parameters'] = format_full_signature_parameters.format(metadata['modifiers'], metadata['type_parameters'], metadata['return'], metadata['parameters']).strip()
        
        metadata['class_method_signature'] = '{}.{}{}'.format(class_identifier, metadata['method_name'], full_parameters_str).strip()

        return metadata


    @staticmethod
    def get_method_name_and_params(function_node, metadata, blob: str):
        '''
        Get focal method name and parameters
        :param function_node:
        :param blob: full context
        :return: dependent classes in parameters
        '''
        declarators = []
        parameters_types = []
        DependencyClassParser.traverse_type(function_node, declarators, '{}_declaration'.format(function_node.type.split('_')[0]))
        full_parameter_list = [] # Incluye typo y nombre
        for n in declarators[0].children: # Solo obtenemos el primero que es el method_declaration
            if n.type == 'identifier':
                metadata['method_name'] = DependencyClassParser.match_from_span(n, blob).strip('(')
            elif n.type == 'formal_parameters':
                full_parameter_list.append(DependencyClassParser.match_from_span(n, blob))
                parameters_types = DependencyClassParser.parse_parameters(n, blob)
        
        #metadata['parameters'] = ' '.join(full_parameter_list)
        metadata['parameters'] = metadata['method_name'] + '(' + ', '.join(parameters_types) + ')'
        metadata['parameters_list'] = parameters_types
        return full_parameter_list


    @staticmethod
    def parse_parameters(param_node, blob: str):
        """
        Get parameter's type, classes, instance&type lists
        in the focal method's parameters.
        """
        #print("\nParam_node: " + str(param_node))
        #print("Param_node text: " + str(param_node.text.decode("utf-8")))
        param_list = []
        for child in param_node.named_children: # Iterate each formal_parameter and spread_parameter (por ejemplo, Integer... values)
            #print("\nParam: " + str(child))
            #print("Param text: " + str(child.text.decode("utf-8")))

            if child.type == "block_comment" or child.type == "line_comment":
                #print("Omitimos comment")
                continue
            
            class_index = 0
            #instance_index = 1
            #print(child.named_children[class_index])
            if child.named_children[0].type == 'modifiers':  # Si el parámetro tiene modificadores, los omitimos
                # Por ejemplo @Nullable final
                #class_index += 1
                #instance_index += 1
                class_index = 1
                #instance_index = 2

            #instance_index = 1
            # class_name = ClassParser.match_from_span(child.child_by_field_name('type'), blob)
            #first_element = DependencyClassParser.match_from_span(child.named_children[0], blob)
            #print(first_element)
            #if ('final' in first_element
            #    or '@' in first_element): # Si el parámetro tiene modificadores, los omitimos
            #    class_index = 1
            #    #instance_index = 2
            
            dimensions_node = child.child_by_field_name('dimensions')

            class_name = DependencyClassParser.match_from_span(child.named_children[class_index], blob)
            if dimensions_node is not None:
                class_name = class_name + "[]"
            
            if not class_name.islower():  # class type
                class_name = class_name.replace(" ", "")

            param_list.append(class_name)

        #print("\n\n\n\n\n")
        return param_list


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
            DependencyClassParser.traverse_type(n, results, kind)


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
            return DependencyClassParser.children_of_type(node, (types,))
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
