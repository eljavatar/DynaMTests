import copy
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser
from typing import List, Dict, Any, Set, Optional
from packaging import version
import pkg_resources


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
    

    def clean_comments(self, src_code: str):
        """
        Parses a java file and extract metadata using info in method_metadata
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
