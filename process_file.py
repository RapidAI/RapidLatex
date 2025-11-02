import os
import re
from process_latex import remove_tex_comments
from encoding import get_file_encoding


def merge_complete(tex):
    '''
    for replace all \input and \include commands by the file content
    '''
    path = f'{tex}.tex'
    dirname = os.path.dirname(path)
    encoding = get_file_encoding(path)
    content = open(path, encoding=encoding).read()
    content = remove_tex_comments(content)

    # Handle both \input{} and \include{} commands
    patterns = [
        (r'\\input{(.*?)}', 'input'),
        (r'\\include{(.*?)}', 'include')
    ]

    # Process all input commands in a single pass to preserve order
    all_matches = []
    for pattern, command_type in patterns:
        pattern_input = re.compile(pattern)
        for match in pattern_input.finditer(content):
            begin, end = match.span()
            filename = match.group(1)

            # Handle .tex extension
            if not filename.endswith('.tex'):
                filename = filename + '.tex'

            full_path = os.path.join(dirname, filename)
            all_matches.append((begin, end, filename, full_path, command_type))

    # Sort matches by position to preserve original order
    all_matches.sort(key=lambda x: x[0])

    # Process matches in reverse order to maintain position offsets correctly
    # This ensures we don't mess up the positions of subsequent input commands
    offset_adjustment = 0
    for begin, end, filename, full_path, command_type in reversed(all_matches):
        print(f'merging {command_type}: {filename}')
        if os.path.exists(full_path):
            encoding = get_file_encoding(full_path)
            new_content = open(full_path, encoding=encoding).read()
            new_content = remove_tex_comments(new_content)
            content = content[:begin] + new_content + content[end:]
        else:
            print(f'Warning: {full_path} not found, skipping {command_type} command')
            # Remove the command but keep a comment
            content = content[:begin] + f'% {command_type}{{{filename}}} (file not found)' + content[end:]

    print(content, file=open(path, "w", encoding='utf-8'))


def add_bbl(tex):
    '''
    for replace \bibliography commands by the corresponding bbl file
    '''
    path_tex = f'{tex}.tex'
    path_bbl = f'{tex}.bbl'

    if not os.path.exists(path_bbl):
        print(f'Warning: {path_bbl} not found, skipping bibliography processing')
        return

    encoding = get_file_encoding(path_tex)
    content = open(path_tex, encoding=encoding).read()
    encoding = get_file_encoding(path_bbl)
    bbl = open(path_bbl, encoding=encoding).read()

    # Remove \bibliographystyle commands but keep them as comments
    content = re.sub(r'\\bibliographystyle\{[^}]*\}', r'% \g<0>', content)

    # Replace \bibliography commands with bbl content
    patterns = [r'\\bibliography\{.*?\}', r'\\thebibliography\{.*?\}']
    bibliography_replaced = False

    for pattern in patterns:
        pattern_input = re.compile(pattern, re.DOTALL)
        while True:
            result = pattern_input.search(content)
            if result is None:
                break
            begin, end = result.span()
            content = content[:begin] + bbl + content[end:]
            bibliography_replaced = True
            print(f'Replaced bibliography command with content from {path_bbl}')

    # If no bibliography commands were found but we have bbl content, add it at the end
    if not bibliography_replaced and os.path.exists(path_bbl):
        print(f'No bibliography command found, appending bibliography at end')
        if content.endswith('\end{document}'):
            content = content.replace('\end{document}', bbl + '\n\n\end{document}')
        else:
            content += '\n\n' + bbl

    print(content, file=open(path_tex, "w", encoding='utf-8'))
