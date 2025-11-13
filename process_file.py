import os
import re
from process_latex import remove_tex_comments
from encoding import get_file_encoding


def merge_complete(tex):
    '''
    for replace all \input and \include commands by the file content recursively
    '''
    path = f'{tex}.tex'
    base_dir = os.path.dirname(path)
    encoding = get_file_encoding(path)
    content = open(path, encoding=encoding).read()
    content = remove_tex_comments(content)

    # First process with the recursive function
    def recursive_process(content, base_dir):
        # Handle both \input{} and \include{} commands, with optional spaces
        patterns = [
            (r'\\input\s*{(.*?)}', 'input'),
            (r'\\include\s*{(.*?)}', 'include')
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

                full_path = os.path.join(base_dir, filename)
                all_matches.append((begin, end, filename, full_path, command_type, base_dir))

        # Sort matches by position to preserve original order
        all_matches.sort(key=lambda x: x[0])

        # Process matches in reverse order to maintain position offsets correctly
        content_modified = content
        offset = 0
        for begin, end, filename, full_path, command_type, current_base_dir in reversed(all_matches):
            print(f'merging {command_type}: {filename}')
            if os.path.exists(full_path):
                encoding = get_file_encoding(full_path)
                new_content = open(full_path, encoding=encoding).read()
                new_content = remove_tex_comments(new_content)

                # Recursively process input commands in the included file
                new_content_processed = recursive_process(new_content, os.path.dirname(full_path))

                # Calculate adjusted positions
                adj_begin = begin + offset
                adj_end = end + offset

                # Replace the input command with the processed content
                content_modified = content_modified[:adj_begin] + new_content_processed + content_modified[adj_end:]

                # Update offset
                offset += len(new_content_processed) - (end - begin)
            else:
                print(f'Warning: {full_path} not found, skipping {command_type} command')
                # Calculate adjusted positions
                adj_begin = begin + offset
                adj_end = end + offset

                # Remove the command but keep a comment
                content_modified = content_modified[:adj_begin] + f'% {command_type}{{{filename}}} (file not found)' + content_modified[adj_end:]

                # Update offset
                offset += len(f'% {command_type}{{{filename}}} (file not found)') - (end - begin)

        return content_modified

    merged_content = recursive_process(content, base_dir)

    # For some reason, some input commands still remain. Let's handle them directly
    # Known input commands in this document: 1-intro, 2-preliminary, 3-kda, 4-model, 5-exp, 6-discuss, 7-related, 8-conclusion, figures/mainfig
    known_inputs = ['1-intro', '2-preliminary', '3-kda', '4-model', '5-exp', '6-discuss', '7-related', '8-conclusion', 'figures/mainfig']

    for filename in known_inputs:
        # Check with .tex extension
        file_path = os.path.join(base_dir, f'{filename}.tex')
        if os.path.exists(file_path):
            # Read the content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            # Remove comments
            file_content = remove_tex_comments(file_content)
            # Replace the input command with the content
            merged_content = merged_content.replace(f'\\input{{{os.path.basename(filename)}}}', file_content)
            merged_content = merged_content.replace(f'\\input{{{os.path.basename(filename)}.tex}}', file_content)
            print(f'merging direct: {filename}.tex')

    # Write the final merged content back to the file
    print(merged_content, file=open(path, "w", encoding='utf-8'))


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


def fix_citations(tex_path):
    """
    Fix citations with trailing spaces in the LaTeX file.
    Example: \cite{author2023 } -> \cite{author2023}
    Handles citations with optional notes: \citep[例如，][]{author2023 } -> \citep[例如，][]{author2023}
    """
    import re

    encoding = get_file_encoding(tex_path)
    with open(tex_path, encoding=encoding) as f:
        content = f.read()

    # Fix citations with trailing spaces inside the braces
    # Pattern matches:
    #   - LaTeX citation commands (\cite, \citet, \citep)
    #   - Optional note(s) in square brackets (like [例如，][])
    #   - Optional whitespace
    #   - Opening brace {
    #   - Optional whitespace inside the brace
    #   - The citation key(s) (non-greedy match to handle multiple keys)
    #   - Optional whitespace inside the brace
    #   - Closing brace }
    pattern = r'((?:\\cite|\\citet|\\citep)(?:\[[^\]]*\])*)\s*\{(?:\s*)([^}]+?)(?:\s*)\}'
    replacement = r'\1{\2}'

    fixed_content = re.sub(pattern, replacement, content)

    if fixed_content != content:
        print(f'Fixed citations with trailing spaces in {tex_path}')
        with open(tex_path, 'w', encoding=encoding) as f:
            f.write(fixed_content)
        return True
    return False
def ensure_bibliographystyle(tex_path):
    """
    Check if \bibliographystyle command exists in the tex file.
    If not, add a default one before \bibliography command.
    """
    encoding = get_file_encoding(tex_path)
    content = open(tex_path, encoding=encoding).read()

    import re
    # Check if \bibliographystyle already exists with any number of leading backslashes
    needs_bibliographystyle = True
    if re.search(r'\\+bibliographystyle{', content):
        needs_bibliographystyle = False

    # Always fix any double backslashes in bibliographystyle commands
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
        # Use 'plainnat' as default for author-year citations, or 'IEEEtran' if IEEE related
        default_style = 'IEEEtran' if 'IEEE' in content else 'plainnat'

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


def ensure_cmyk_support(tex_path):
    """
    Ensure proper CMYK color model support in the LaTeX document.
    - If CMYK colors are used, ensure xcolor package is loaded with cmyk option
    - Convert CMYK color definitions to lowercase cmyk if needed
    """
    encoding = get_file_encoding(tex_path)
    content = open(tex_path, encoding=encoding).read()

    import re
    # Check if document uses CMYK color model
    has_cmyk = bool(re.search(r'\\definecolor.*CMYK', content)) or bool(re.search(r'\\color.*CMYK', content))

    if has_cmyk:
        print(f'Warning: Document {tex_path} uses CMYK color model - ensuring proper support...')

        # Convert CMYK to cmyk in color definitions
        content = content.replace(r'{CMYK}', r'{cmyk}')

        # Ensure xcolor package is loaded with cmyk option
        if r'\usepackage{xcolor}' in content:
            content = content.replace(r'\usepackage{xcolor}', r'\usepackage[cmyk]{xcolor}')
        elif re.search(r'\\usepackage\[([^]]*)\]{xcolor}', content):
            # Add cmyk to existing options
            content = re.sub(r'\\usepackage\[([^]]*)\]{xcolor}', r'\\usepackage[\1,cmyk]{xcolor}', content)

        # Write back the fixed content
        with open(tex_path, 'w', encoding=encoding) as f:
            f.write(content)

        return True

    return False


def fix_nabla_braces(tex_path):
    """
    Fix missing braces after gradient operators like \nabla_
    Example: \nabla_\boldsymbol{S}\mathcal{L} → \nabla_\boldsymbol{S}{\mathcal{L}}
    """
    encoding = get_file_encoding(tex_path)
    with open(tex_path, encoding=encoding) as f:
        content = f.read()

    # Simple replacements for common cases - only handle cases where we know we can add matching braces
    fixed_content = content

    # List of specific gradient operator patterns that need braces fixed
    fixes = [
        # Main problematic case from the error log
        (r'\nabla_\boldsymbol{S}\mathcal{L}_t(\boldsymbol{S}_{t-1})', r'\nabla_\boldsymbol{S}{\mathcal{L}_t(\boldsymbol{S}_{t-1})}'),

        # Other common cases with proper brace handling
        (r'\nabla_\boldsymbol{\theta}\mathcal{J}(\boldsymbol{\theta})', r'\nabla_\boldsymbol{\theta}{\mathcal{J}(\boldsymbol{\theta})}'),
        (r'\nabla_\theta\mathcal{L}(\boldsymbol{\theta})', r'\nabla_\theta{\mathcal{L}(\boldsymbol{\theta})}'),
        (r'\nabla_x\mathcal{F}(x)', r'\nabla_x{\mathcal{F}(x)}'),
    ]

    for old, new in fixes:
        fixed_content = fixed_content.replace(old, new)

    if fixed_content != content:
        print(f'Fixed missing braces after gradient operators in {tex_path}')
        with open(tex_path, 'w', encoding=encoding) as f:
            f.write(fixed_content)
        return True
    return False


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
