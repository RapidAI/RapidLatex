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


import os

def add_bbl(tex):
    '''
    Modified to preserve \input{*.bbl} commands without expanding bibliography content.
    This function now only handles \bibliographystyle commands and preserves \input{*.bbl} as-is.
    '''
    path_tex = f'{tex}.tex'
    path_bbl = f'{tex}.bbl'

    # Try to extract bbl from input tar if it's missing
    if not os.path.exists(path_bbl):
        import tarfile
        import shutil

        # Check if input tar exists
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tex_dir = os.path.dirname(tex)
        basename = os.path.basename(tex)

        # Try to extract bbl from the temporary directory or input tar
        # First check if we're in output directory
        if 'output' in tex_dir:
            # Extract arxiv id from output path
            arxiv_id = basename
            input_tar_path = os.path.join(base_dir, 'input', f'{arxiv_id}.tar.gz')
        else:
            # In temp directory during processing
            input_tar_path = None

        if input_tar_path and os.path.exists(input_tar_path):
            print(f'Looking for bbl file in input tar...')
            with tarfile.open(input_tar_path, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('.bbl'):
                        print(f'Found {member.name} in input tar, extracting...')
                        tar.extract(member, path=os.path.dirname(path_bbl))
                        print('Successfully extracted bbl file from input tar!')
                        break

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
        print(f'No \\input{{*.bbl}} command found in {path_tex}, adding it to include bibliography content')
        # Find the bibliography command and replace it with input command
        bib_pattern = re.compile(r'\\bibliography\{[^}]*\}', re.IGNORECASE)
        if bib_pattern.search(content):
            content = bib_pattern.sub(r'\\input{main.bbl}', content)
        else:
            # If no bibliography command found, add it at the end before \end{document}
            end_doc_pattern = re.compile(r'\\end\{document\}', re.IGNORECASE)
            if end_doc_pattern.search(content):
                content = end_doc_pattern.sub(r'\\input{main.bbl}\n\\end{document}', content)
            else:
                # Fallback: add at the end of the file
                content += '\n\\input{main.bbl}\n'

    # Write back the content with \bibliographystyle commented out and \input{*.bbl} added if needed
    with open(path_tex, "w", encoding='utf-8') as f:
        f.write(content)


def ensure_bibliographystyle(tex_path):
    """
    Check if \bibliographystyle command exists in the tex file.
    If not, add a default one before \bibliography command.
    """
    encoding = get_file_encoding(tex_path)
    content = open(tex_path, encoding=encoding).read()

    # Check if \bibliographystyle already exists (look for actual pattern with backslash)
    # Need to check for both single and double backslash versions
    needs_bibliographystyle = True
    for pattern in [r'\\bibliographystyle{', r'\\\\bibliographystyle{']:
        if pattern in content:
            needs_bibliographystyle = False
            break

    # Fix any double backslashes in bibliographystyle commands
    if not needs_bibliographystyle:
        content = content.replace(r'\\bibliographystyle{', r'\bibliographystyle{')

    # Check if \bibliography exists
    if 'bibliography{' not in content.lower():
        return False  # No bibliography, nothing to fix

    # Find position of bibliography
    bib_pos = content.lower().find('bibliography{')
    if bib_pos < 0:
        return False

    # Fix any double backslashes in bibliography commands first
    content = content.replace(r'\\bibliography{', r'\bibliography{')

    # Re-find position of bibliography in case we fixed backslashes
    bib_pos = content.lower().find('bibliography{')
    if bib_pos < 0:
        return False

    # Check if \bibliography has correct backslash (fix if missing)
    has_backslash = bib_pos > 0 and content[bib_pos-1] == '\\'

    if not has_backslash:
        print(f'Warning: \\bibliography command missing backslash - Adding backslash...')
        content = content[:bib_pos] + '\\' + content[bib_pos:]
        bib_pos += 1  # Adjust position after adding backslash

    # Only add bibliographystyle if it doesn't exist yet
    if needs_bibliographystyle:
        # Create a mock match object
        class MockMatch:
            def __init__(self, pos):
                self.start = lambda: pos
        bib_match = MockMatch(bib_pos)

        # Add default \bibliographystyle before \bibliography
        # Use 'plain' as default, or 'IEEEtran' if IEEE related
        default_style = 'IEEEtran' if 'IEEE' in content else 'plain'

        print(f'Warning: No \\bibliographystyle found in {tex_path}')
        print(f'Adding default \\bibliographystyle{{{default_style}}} before \\bibliography')

        # Insert \bibliographystyle before \bibliography
        bib_start = bib_match.start()
        style_command = f'\\bibliographystyle{{{default_style}}}\n'

        content = content[:bib_start] + style_command + content[bib_start:]

    # Write back the file
    with open(tex_path, 'w', encoding=encoding) as f:
        f.write(content)

    return True


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
