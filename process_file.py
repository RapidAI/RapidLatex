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

            # Skip .bbl files - they should remain as \input{*.bbl} commands
            if filename.endswith('.bbl'):
                print(f'skipping .bbl file: {filename} (preserving \\input command)')
                continue

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
    Modified to preserve \input{*.bbl} commands without expanding bibliography content.
    This function now only handles \bibliographystyle commands and preserves \input{*.bbl} as-is.
    '''
    path_tex = f'{tex}.tex'
    path_bbl = f'{tex}.bbl'

    if not os.path.exists(path_bbl):
        print(f'Warning: {path_bbl} not found, but preserving \input commands anyway')
        return

    encoding = get_file_encoding(path_tex)
    content = open(path_tex, encoding=encoding).read()

    # Remove \bibliographystyle commands but keep them as comments
    content = re.sub(r'\\bibliographystyle\{[^}]*\}', r'% \g<0>', content)

    # Check if \input{*.bbl} command exists in the file
    bbl_input_pattern = re.compile(r'\\input\{.*?\.bbl\}')
    if bbl_input_pattern.search(content):
        print(f'Found \\input{{*.bbl}} command in {path_tex}, preserving it without expansion')
    else:
        print(f'No \\input{{*.bbl}} command found in {path_tex}, but .bbl file exists')

    # Write back the content with \bibliographystyle commented out but preserving \input{*.bbl}
    print(content, file=open(path_tex, "w", encoding='utf-8'))


def generate_bbl_from_bib(tex_path):
    """
    Generate .bbl file from .bib references.
    Looks for \bibliography{refname} command and tries to find corresponding .bib file.
    If found, compiles it to generate .bbl file using bibtex.
    """
    import subprocess

    # Read tex file
    encoding = get_file_encoding(tex_path)
    content = open(tex_path, encoding=encoding).read()

    # Look for \bibliography{...} command
    bib_pattern = r'\\bibliography\\{([^}]+)\\}'
    bib_match = re.search(bib_pattern, content)

    if not bib_match:
        return False

    bib_name = bib_match.group(1)
    bib_path = f'{bib_name}.bib'
    bbl_path = f'{bib_name}.bbl'

    # Check if .bib file exists
    if not os.path.exists(bib_path):
        print(f'Warning: Bibliography file {bib_path} referenced in {tex_path} not found')
        return False

    # Check if .bbl file already exists
    if os.path.exists(bbl_path):
        print(f'.bbl file {bbl_path} already exists, skipping generation')
        return True

    # Try to generate .bbl file
    print(f'Generating .bbl file from {bib_path}...')

    try:
        # Create a minimal aux file to run bibtex
        aux_content = '\\relax\n' + '\\citation{*}\n' + f'\\bibdata{{{bib_name}}}\n' + '\\bibstyle{plain}\n'

        with open(f'{bib_name}.aux', 'w', encoding='utf-8') as f:
            f.write(aux_content)

        # Run bibtex
        result = subprocess.run(['bibtex', f'{bib_name}.aux'],
                              capture_output=True, text=True, timeout=30)

        # Check if .bbl was generated
        if os.path.exists(f'{bib_name}.bbl'):
            print(f'Successfully generated {bib_name}.bbl from {bib_name}.bib')

            # Clean up aux files
            for ext in ['.aux', '.blg', '.log']:
                temp_file = f'{bib_name}{ext}'
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass

            return True
        else:
            print(f'Failed to generate .bbl file. BibTeX output: {result.stderr}')
            return False

    except FileNotFoundError:
        print('Warning: bibtex command not found. Cannot generate .bbl file from .bib')
        return False
    except Exception as e:
        print(f'Error generating .bbl file: {e}')
        return False
