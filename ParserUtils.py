import copy
import textwrap
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser, Node
from typing import List, Dict, Any, Set, Optional
from packaging import version
import pkg_resources
import re


class ParserUtils():

    def __init__(self, input_encoding):
        tree_sitter_version = pkg_resources.get_distribution("tree_sitter").version

        if version.parse(str(tree_sitter_version)) < version.parse("0.22.0"):
            JAVA_LANGUAGE = Language(tsjava.language(), "java")
        else:
            JAVA_LANGUAGE = Language(tsjava.language())

        self.parser = Parser()
        self.parser.set_language(JAVA_LANGUAGE)
        self.input_encoding = input_encoding
    

    def validate_if_code_has_errors(self, src_code: str, validate_all_errors: bool):
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        #src_decoded = src_encoded_bytes.decode(self.input_encoding)
        #print("\n" + str(src_decoded))

        tree = self.parser.parse(src_encoded_bytes)
        content_node_main = tree.root_node

        if validate_all_errors:
            return content_node_main.has_error

        list_missing_nodes: List[Node] = []
        ParserUtils.traverse_tree_missing(content_node_main, list_missing_nodes)

        list_only_errors_nodes: List[Node] = []
        ParserUtils.traverse_tree_only_errors(content_node_main, list_only_errors_nodes)

        only_has_identifier_missings = True
        for missing_node in list_missing_nodes:
            # value_missing = missing_node.text.decode(self.input_encoding).strip()
            # value_missing = ParserUtils.match_from_span(missing_node, src_code)
            # print(f"Value missing: |{str(missing_node.type)}|")
            if str(missing_node.type) != "identifier":
                only_has_identifier_missings = False
                break

        # Escenarios validos
        # Si only_errors vacio y only_has_identifier_missings es True
        if len(list_only_errors_nodes) == 0 and only_has_identifier_missings:
            return False
        
        #print("Has errors: " + str(content_node_main.has_error))

        return content_node_main.has_error
    

    def method_body_is_empty(self, src_code: str):
        """
        Parses a fragment code and validate if its empty or not
        """
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        tree = self.parser.parse(src_encoded_bytes)
        
        program_node_main = tree.root_node
        if program_node_main is None or len(program_node_main.children) == 0:
            return True

        method_declaration_node = program_node_main.children[0]
        if method_declaration_node is None or len(method_declaration_node.children) == 0:
            return True

        body_node = method_declaration_node.child_by_field_name('body')
        if body_node is None:
            return True
        
        body_node_text = body_node.text.decode(self.input_encoding).strip()
        if len(body_node_text) == 0:
            return True

        # print()
        # print(program_node_main.type)
        # print(program_node_main)
        # print(method_declaration_node.type)
        # print(method_declaration_node)
        # print(body_node)
        # print(body_node_text)

        body_block = body_node_text[1 : -1].strip()
        return len(body_block) == 0
    

    def clean_comments(self, src_code: str):
        """
        Parses a fragment code and delete line and block comments
        """

        #src_encoded_bytes = src_code.encode(encoding="utf-8")
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        src_decoded = src_encoded_bytes.decode(self.input_encoding)

        #try:
        #    src_decoded = src_encoded_bytes.decode("cp1252")
        #except:
        #    src_decoded = src_encoded_bytes.decode("utf-8")

        #src_decoded = src_encoded_bytes.decode("cp1252", errors="ignore")

        clean_code = src_decoded

        #Build Tree
        #tree = self.parser.parse(src_encoded_bytes)
        tree = self.parser.parse(src_encoded_bytes)
        #tree = self.parser.parse(bytes(src_code.encode(encoding="utf-8", errors="ignore").decode("utf-8"), "utf8"))
        #tree = self.parser.parse(bytes(src_code.encode(encoding=self.input_encode, errors="ignore").decode("utf-8"), "utf8"))
        content_node_main = tree.root_node

        #tree_copy = copy.deepcopy(tree)
        #tree_copy
        #tree_copy = tree
        #tree_copy.edit()

        #edited_code = src_decoded

        block_comments_nodes = []
        ParserUtils.traverse_type(content_node_main, block_comments_nodes, "block_comment")
        for block_comment_node in block_comments_nodes:
            #block_comment_str = ParserUtils.match_from_span(block_comment_node, src_code)
            block_comment_text = block_comment_node.text.decode(self.input_encoding)

            #if 'Coin.valueOf(-1234567890l)' in src_code:
            #    print("Block Coment: '" + block_comment_str + "'")
            clean_code = clean_code.replace(block_comment_text, " ")


        line_comments_nodes = []
        list_line_comments_str = []
        ParserUtils.traverse_type(content_node_main, line_comments_nodes, "line_comment")
        for line_comment_node in line_comments_nodes:
            #line_comment_str = ParserUtils.match_from_span(line_comment_node, src_decoded)
            line_comment_text = line_comment_node.text.decode(self.input_encoding)
            
            list_line_comments_str.append(line_comment_text)

        # Esto se hace para casos en los que se tienen líneas de comentarios como las siguientes:
        # // one comment
        # // another comment // one comment
        # En estos casos, si se elimina primero el comentario "// one comment", después no
        # sería posible encontrar el comentario "// another comment // one comment".
        # Por eso se ordenan los comentarios según la longitud de cada uno de ellos
        # de mayor a menor, de esta forma, se eliminaría primero "// another comment // one comment"
        # y después "// one comment"
        list_line_comments_order_desc_by_len = reversed(sorted(list_line_comments_str, key=lambda item: len(item)))
        for line_comment_to_clean in list_line_comments_order_desc_by_len:
            clean_code = clean_code.replace(line_comment_to_clean, " ")

        try:
            clean_code = clean_code.encode(self.input_encoding).decode("utf-8")
        except:
            pass
        
        return clean_code
    

    def clean_annotations(self, src_code: str):
        """
        Parses a fragment code and delete annotations
        """
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        src_decoded = src_encoded_bytes.decode(self.input_encoding)

        clean_code = src_decoded

        tree = self.parser.parse(src_encoded_bytes)
        content_node_main = tree.root_node

        list_annotations = []

        annotations_nodes = []
        ParserUtils.traverse_type(content_node_main, annotations_nodes, "annotation")
        for annotation_node in annotations_nodes:
            annotation_text = annotation_node.text.decode(self.input_encoding)
            # clean_code = clean_code.replace(annotation_text, "")
            list_annotations.append(annotation_text)

        marker_annotations_nodes = []
        ParserUtils.traverse_type(content_node_main, marker_annotations_nodes, "marker_annotation")
        for marker_annotation_node in marker_annotations_nodes:
            marker_annotation_text = marker_annotation_node.text.decode(self.input_encoding)
            # clean_code = clean_code.replace(marker_annotation_text, "")
            list_annotations.append(marker_annotation_text)
        
        # Esto se hace para casos en los que se tienen anotaciones las siguientes:
        # @Service @ServiceImpl public class ...
        # En estos casos, si se elimina primero la anotación @Service, después no
        # sería posible encontrar la anotación @ServiceImpl.
        # Por eso se ordenan las anotaciones según la longitud de cada uno de ellas
        # de mayor a menor, de esta forma, se eliminaría primero @ServiceImpl
        # y después @Service
        list_annotations_order_desc_by_len = reversed(sorted(list_annotations, key=lambda item: len(item)))
        for annotation_to_clean in list_annotations_order_desc_by_len:
            clean_code = clean_code.replace(annotation_to_clean, "")

        try:
            clean_code = clean_code.encode(self.input_encoding).decode("utf-8")
        except:
            pass
        
        return clean_code.strip()
    

    def clean_signatures_annotations(self, src_code: str):
        """
        Parses a fragment code and delete signature annotations
        """
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        src_decoded = src_encoded_bytes.decode(self.input_encoding)

        clean_code = src_decoded
        # edited_code = src_decoded

        tree = self.parser.parse(src_encoded_bytes)
        program_node_main = tree.root_node

        if program_node_main is None or len(program_node_main.children) == 0:
            return clean_code
        
        length_reduced = 0
        for child in program_node_main.children:
            if child.type == 'method_declaration':
                method_declaration_children = child.children
                
                for _child in method_declaration_children:
                    if _child.type == 'modifiers':
                        modifiers_chilren = _child.children
                        
                        for c in modifiers_chilren:
                            if c.type == 'marker_annotation' or c.type == 'annotation':
                                
                                annotation_text = c.text.decode(self.input_encoding)
                                # print(f"Annotation type {c.type} - Value: {annotation_text}")
                                # clean_code = clean_code.replace(annotation_text, "")
                                clean_code = clean_code[: c.start_byte - length_reduced] + clean_code[c.end_byte - length_reduced :]
                                length_reduced += len(annotation_text)
                                
                                # print("")
                                # print(f"length annotation: {len(annotation_text)}")
                                # print(f"points annotation: [{c.start_byte} - {c.end_byte}]")
                                # print(f"Index start: {(c.start_byte - length_reduced)}")
                                # print(f"Before: |{edited_code}| -> old length: {len(edited_code)}")
                                # edited_code = edited_code[: c.start_byte - length_reduced] + edited_code[c.end_byte - length_reduced :]
                                # print(f"After:  |{edited_code}| -> new length: {len(edited_code)}")
                                # length_reduced += len(annotation_text)
                                # print(f"total length reduced: {length_reduced}")
        
        # Reemplaza múltiples espacios por un solo espacio
        clean_code = re.sub(r'\s{2,}', ' ', clean_code)
        # print(f"\n\nFinal:\n{edited_code}\n\n")
        
        try:
            clean_code = clean_code.encode(self.input_encoding).decode("utf-8")
        except:
            pass
        
        return clean_code.strip()


    # Revisar para ajustar estos casos al momento de hacer el minado
    def fix_close_type_parameter_sig_class(self, sig_class: str):
        """
        En el minado, para el caso de las firmas las clases con tipos genéricos,
        por ejemplo: public class SomeClass<T>, en algunos casos quedó de la siguiente manera:
        public class SomeClass<T. Por tanto, con este método se ajustan esos casos
        """
        sig_class_valid = sig_class + " { }"

        src_encoded_bytes = bytes(sig_class_valid, self.input_encoding)
        src_decoded = src_encoded_bytes.decode(self.input_encoding)

        edited_code = src_decoded

        tree = self.parser.parse(src_encoded_bytes)
        program_node_main = tree.root_node

        list_missing_nodes: List[Node] = []
        ParserUtils.traverse_tree_missing(program_node_main, list_missing_nodes)

        length_aument = 0
        for missing_node in list_missing_nodes:
            if str(missing_node.type) == ">":
                edited_code = edited_code[: missing_node.start_byte + length_aument] + str(missing_node.type) + edited_code[missing_node.start_byte + length_aument :]
                length_aument += len(str(missing_node.type))
        
        try:
            edited_code = edited_code.encode(self.input_encoding).decode("utf-8")
        except:
            pass

        edited_code = edited_code.replace("{", "").replace("}", "")

        return edited_code.strip()



    # Revisar para ajustar estos casos al momento de hacer el minado
    def fix_type_parameters_inconsistences(self, src_code: str):
        """
        En el minado, para el caso de las firmas de constructores que tiene tipos genéricos,
        por ejemplo: public <T> MyConstructor(), quedaron de la siguiente manera:
        public<T> <T> MyConstructor(). Por tanto, con este método se ajustan esos casos
        """

        src_encoded_bytes = bytes(src_code, self.input_encoding)
        src_decoded = src_encoded_bytes.decode(self.input_encoding)

        clean_code = src_decoded

        tree = self.parser.parse(src_encoded_bytes)
        program_node_main = tree.root_node

        if program_node_main is None or len(program_node_main.children) == 0:
            return clean_code

        list_only_errors_nodes: List[Node] = []
        ParserUtils.traverse_tree_only_errors(program_node_main, list_only_errors_nodes)

        length_reduced = 0
        for error_node in list_only_errors_nodes:
            # print(str(error_node))
            if len(error_node.children) > 0:
                error_detail_node = error_node.children[0]
                # print(error_detail_node)
                # print("Type error: " + str(error_detail_node.type))
                if error_detail_node.type == 'type_parameters':
                    error_text = error_detail_node.text.decode(self.input_encoding)
                    clean_code = clean_code[: error_detail_node.start_byte - length_reduced] + clean_code[error_detail_node.end_byte - length_reduced :]
                    length_reduced += len(error_text)

            # print()

        # Reemplaza múltiples espacios por un solo espacio
        clean_code = re.sub(r'\s{2,}', ' ', clean_code)
        # print(f"\n\nFinal:\n{edited_code}\n\n")
        
        try:
            clean_code = clean_code.encode(self.input_encoding).decode("utf-8")
        except:
            pass
        
        return clean_code.strip()


    def get_body_methods_from_class(self, src_code: str) -> set[str]:
        src_encoded_bytes = bytes(src_code, self.input_encoding)
        tree = self.parser.parse(src_encoded_bytes)
        content_node_main = tree.root_node

        method_declarations_nodes = []
        ParserUtils.traverse_type(content_node_main, method_declarations_nodes, "method_declaration")

        list_body_methods: set[str] = set()

        for method_declaration_node in method_declarations_nodes:
            body_method_text = method_declaration_node.text.decode(self.input_encoding)
            # clean_code = clean_code.replace(annotation_text, "")
            list_body_methods.add(body_method_text.strip())
        
        return list_body_methods



    @staticmethod
    def traverse_tree_missing(node: Node, results: List):
        for n in node.children:
            if n.is_missing: 
                results.append(n)
            ParserUtils.traverse_tree_missing(n, results)
    

    @staticmethod
    def traverse_tree_only_errors(node: Node, results: List):
        for n in node.children:
            if n.is_error and not n.is_missing: 
                results.append(n)
            ParserUtils.traverse_tree_only_errors(n, results)
    

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
            ParserUtils.traverse_type(n, results, kind)


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
            return ParserUtils.children_of_type(node, (types,))
        return [child for child in node.children if child.type in types]
    

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


# parser_utils = ParserUtils("utf-8")

# class_sig = "public abstract class ContainerId implements Comparable<ContainerId"
# print(parser_utils.fix_close_type_parameter_sig_class(class_sig))

# src_code = textwrap.dedent("""
# @SuppressWarnings({"squid:S2095", // SonarQube doesn't realize that the cursor is wrapped and returned
#                    "PMD.CompareObjectsWithEquals"})
# protected RecordCursor<ResolvedKeySpacePath> listSubdirectoryAsync(@Nullable KeySpacePath listFrom,
#                                                                    @Nonnull FDBRecordContext context,
#                                                                    @Nonnull String subdirName,
#                                                                    @Nullable ValueRange<?> valueRange,
#                                                                    @Nullable byte[] continuation,
#                                                                    @Nonnull ScanProperties scanProperties);
# """)

# src_code = textwrap.dedent(""""
# @Nonnull @SuppressWarnings({\"squid:S2095\", // SonarQube doesn't realize that the cursor is wrapped and returned \"PMD.CompareObjectsWithEquals\"}) protected RecordCursor<ResolvedKeySpacePath> listSubdirectoryAsync(@Nullable KeySpacePath listFrom,\n                                                                       @Nonnull FDBRecordContext context,\n                                                                       @Nonnull String subdirName,\n                                                                       @Nullable ValueRange<?> valueRange,\n                                                                       @Nullable byte[] continuation,\n                                                                       @Nonnull ScanProperties scanProperties)
# """)

# clean_code = parser_utils.clean_comments(src_code)
# #clean_code = re.sub(r'\s{2,}', ' ', clean_code)
# print(clean_code)



# imports = "import java.net;|import // line comment\n /* block commetn */ sql.data;"
# print(clean_tabs_and_new_lines(parser_utils.clean_comments(imports)))
# print("Imports: " + parser_utils.clean_comments(""))

# code = "@Test public void method() { }"
# validate = parser_utils.method_body_is_empty(code)
# print(validate)

# methods = '@Entity private String val1; @Suppress(@Another) @Test public void method1(); @Override("value") @Test(@Another) public void method2(); @Override2("value") @Test2(@Another2) public void method4(); void method3();'
# print("\n")
# print(parser_utils.clean_signatures_annotations(methods))

# class_signature = '@Service @Test @TestCase @Supress({@Service}) public class MyClass'
# print()
# print(parser_utils.clean_annotations(class_signature))

# src_code = "public Source(String filePath); public Source(String filePath, LineMap lineMap); public File getFile():"
# print("\n")
# print(str(parser_utils.validate_if_code_has_errors(src_code)))

# src_code = "private<D> <D> InjectableMethod(@Nullable TypeLiteral < D > targetType, @Nullable D target, Method method, @Nullable T result); private < D > < D > InjectableMethod(@Nullable TypeLiteral<D> targetType); public boolean hasReturnValue(final String value, , Long num);"
# print("\n")
# print(parser_utils.fix_type_parameters_inconsistences(src_code))
