#!/usr/bin/env python
import os
__version__ = open(os.path.join(os.path.dirname(__file__), 'version.txt'), encoding='utf-8').read().strip()
import process_latex
import process_text
import cache
from config import config
from process_latex import environment_list, command_list, format_list
from process_text import char_limit
from encoding import get_file_encoding
import time
import re
import tqdm.auto
import concurrent.futures
default_begin = r'''
\documentclass[UTF8]{article}
\usepackage{xeCJK}
\usepackage{amsmath,amssymb}
\begin{document}
'''
default_end = r'''
\end{document}
'''


class TextTranslator:
    def __init__(self, engine, language_to, language_from):
        self.engine = engine
        if engine == 'google':
            import mtranslate as translator
            self.translator = translator
            # Add timeout and retry logic for Google Translate
            import signal
            import threading

            def safe_translate(text, lang_to, lang_from, timeout=10):
                """Translate text with timeout to prevent hanging"""
                result = [None]
                exception = [None]

                def translate_thread():
                    try:
                        result[0] = translator.translate(text, lang_to, lang_from)
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=translate_thread)
                thread.daemon = True
                thread.start()
                thread.join(timeout)

                if thread.is_alive():
                    # Translation timed out
                    print(f"Warning: Translation timed out for text: {text[:50]}...")
                    return text  # Return original text if timeout

                if exception[0]:
                    print(f"Warning: Translation failed: {exception[0]}")
                    return text  # Return original text if error

                return result[0]

            self.try_translate = lambda text: safe_translate(text, self.language_to, self.language_from)
            #from mathtranslate.google import ParallelTranslator
            #self.translator = ParallelTranslator(language_to, language_from)
            #self.try_translate = lambda text: self.translator.translate(text)
        elif engine == 'tencent' or engine == 'tencentcloud':
            from tencent import Translator
            self.translator = Translator(
                secret_id=config.tencent_secret_id,
                secret_key=config.tencent_secret_key,
                region=config.tencent_region
            )
            self.try_translate = lambda text: self.translator.translate(text, self.language_to, self.language_from)
        elif engine == 'openai':
            from openai_translator import OpenAITranslator
            self.translator = OpenAITranslator(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
                model=config.openai_model,
                max_tokens=config.openai_max_tokens,
                temperature=config.openai_temperature,
                chunk_size=config.openai_chunk_size
            )
            self.try_translate = lambda text: self.translator.translate(text, self.language_to, self.language_from)
        else:
            assert False, "engine must be google, tencent, tencentcloud, or openai"
        self.language_to = language_to
        self.language_from = language_from
        self.number_of_calls = 0
        self.tot_char = 0

    def translate(self, text):
        if not re.match(re.compile(r'.*[a-zA-Z].*', re.DOTALL), text):
            # no meaningful word inside
            return text
        while True:
            try:
                result = self.try_translate(text)
                break
            except BaseException as e:
                if hasattr(self.translator, "is_error_request_frequency") and self.translator.is_error_request_frequency(e):
                    time.sleep(0.5)
                else:
                    raise e
        self.number_of_calls += 1
        self.tot_char += len(text)
        return result


class LatexTranslator:
    def __init__(self, translator: TextTranslator, debug=False, threads=0):
        self.translator = translator
        self.debug = debug
        if self.debug:
            self.f_old = open("text_old", "w", encoding='utf-8')
            self.f_new = open("text_new", "w", encoding='utf-8')
            self.f_obj = open("objs", "w", encoding='utf-8')
        if threads == 0:
            self.threads = None
        else:
            self.threads = threads

    def close(self):
        if self.debug:
            self.f_old.close()
            self.f_new.close()
            self.f_obj.close()

    def translate_paragraph_text(self, text):
        '''
        Translators would have a word limit for each translation
        So here we split translation by '\n' if it's going to exceed limit
        '''
        lines = text.split('\n')
        parts = []
        part = ''
        for line in lines:
            if len(line) >= char_limit:
                assert False, "one line is too long"
            if len(part) + len(line) < char_limit - 10:
                part = part + '\n' + line
            else:
                parts.append(part)
                part = line
        parts.append(part)
        parts_translated = []
        for part in parts:
            text_original = part.strip()
            if text_original.upper() == text_original:
                result = text_original
            else:
                # ENHANCED: Protect XMATHX placeholders and associated command names from translation
                import re
                xm_placeholders = re.findall(r'XMATHX[A-Z_]*', text_original)
                if xm_placeholders:
                    # Ensure XMATHX patterns are in skip_commands for protection
                    for placeholder in xm_placeholders:
                        base_pattern = placeholder.split('_')[0]  # Get 'XMATHX' part
                        if base_pattern not in config.skip_commands:
                            config.skip_commands.append(base_pattern)
                        if placeholder not in config.skip_commands:
                            config.skip_commands.append(placeholder)

                    # NEW: Also protect LaTeX command names that follow XMATHX placeholders
                    # This prevents commands like "bibliographystyle" from being translated
                    # when they appear after XMATHXBS placeholders
                    command_pattern = r'XMATHX[A-Z_]*\s+(\w+)(?:\s*\{[^}]*\})*'
                    command_matches = re.findall(command_pattern, text_original)
                    if command_matches:
                        for command_name in command_matches:
                            if command_name not in config.skip_commands:
                                config.skip_commands.append(command_name)

                result = self.translator.translate(text_original)
            parts_translated.append(result)
        text_translated = '\n'.join(parts_translated)
        return text_translated.replace("\u200b", "")

    def replace_with_uppercase(self, text, word):
        # Construct a regex pattern that matches the word regardless of case
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        # Replace all matches with the uppercase version of the word
        result = pattern.sub(word.upper(), text)
        return result

    def _translate_text_in_paragraph_latex(self, latex_original_paragraph):
        '''
        Translate a latex paragraph, which means that it could contain latex objects
        '''

        # ENHANCED: Apply bibliography formatting fix BEFORE translation
        # This ensures missing backslashes are added so object recognition can properly protect commands
        def fix_bibliography_formatting(text):
            """Fix bibliography formatting issues in LaTeX text."""
            # Fix missing backslashes on bibliography commands
            text = re.sub(r'(?<!\\)(bibliographystyle|bibliography)(?=\s*\{)', r'\\\1', text)

            # Fix double backslash issues
            text = re.sub(r'\\\\(bibliographystyle|bibliography)', r'\\\1', text)
            # Also handle the case where we have space + double backslash
            text = re.sub(r'\\ \\(bibliographystyle|bibliography)', r'\\\1', text)

            # Fix spaces after backslashes
            text = re.sub(r'\\\s+(bibliographystyle|bibliography)', r'\\\1', text)
            text = re.sub(r'\\ (bibliographystyle|bibliography)', r'\\\1', text)

            # Fix extra spaces inside braces for bibliography commands
            text = re.sub(r'(\\(?:bibliographystyle|bibliography)\s*\{)\s*([^}]+?)\s*(\})',
                          lambda m: m.group(1) + m.group(2).strip() + m.group(3), text)

            return text

        latex_original_paragraph = fix_bibliography_formatting(latex_original_paragraph)

        # remove format about textbf, emph and textit
        for format_name in format_list:
            latex_original_paragraph = process_latex.delete_specific_format(latex_original_paragraph, format_name)

        text_original_paragraph, objs = process_latex.replace_latex_objects(latex_original_paragraph)
        # Since \n is equivalent to space in latex, we change \n back to space
        # otherwise the translators view them as separate sentences
        text_original_paragraph = process_latex.combine_split_to_sentences(text_original_paragraph)
        text_original_paragraph = process_text.split_too_long_paragraphs(text_original_paragraph)
        if not self.complete:
            text_original_paragraph = process_text.split_titles(text_original_paragraph)
        # Remove additional space
        text_original_paragraph = re.sub(r'  +', ' ', text_original_paragraph)
        if self.debug:
            print(f'\n\nParagraph {self.num}\n\n', file=self.f_old)
            print(text_original_paragraph, file=self.f_old)
        text_translated_paragraph = self.translate_paragraph_text(text_original_paragraph)
        text_translated_paragraph = self.replace_with_uppercase(text_translated_paragraph, config.math_code)
        if self.debug:
            print(f'\n\nParagraph {self.num}\n\n', file=self.f_new)
            print(text_translated_paragraph, file=self.f_new)
            print(f'\n\nParagraph {self.num}\n\n', file=self.f_obj)
            for i, obj in enumerate(objs):
                print(f'obj {i}', file=self.f_obj)
                print(obj, file=self.f_obj)
        latex_translated_paragraph, nbad, ntotal = process_latex.recover_latex_objects(text_translated_paragraph, objs, tolerate_error=True)
        self.nbad += nbad
        self.ntotal += ntotal
        return latex_translated_paragraph

    def translate_text_in_paragraph_latex(self, paragraph):
        splited_paragraphs, seps = process_latex.split_by_command(paragraph)
        result = ''
        for split, sep in zip(splited_paragraphs, seps):
            result += self._translate_text_in_paragraph_latex(split) + ' ' + sep + ' '
        return result

    def translate_latex_all_objects(self, latex):
        '''
        Terminology:
        env: '\\begin{xxx} \\end{xxx}'
        command: '\\command[options]{text}
        object: env or command
        '''
        translate_function = self.translate_text_in_paragraph_latex_and_leading_brace

        # Build comprehensive environment and command lists
        all_environments = []
        all_commands = []

        # Add default environments (minus skip list)
        for env_name in environment_list + self.theorems:
            if env_name not in config.skip_environments:
                all_environments.append(env_name)

        # Add custom environments
        for env_name in config.custom_environments:
            if env_name not in config.skip_environments:
                all_environments.append(env_name)

        # Add default commands (minus skip list)
        for command_name in command_list:
            if command_name not in config.skip_commands:
                all_commands.append(command_name)

        # Add custom commands
        for command_name in config.custom_commands:
            if command_name not in config.skip_commands:
                all_commands.append(command_name)

        # Process environments
        for env_name in all_environments:
            latex = process_latex.process_specific_env(latex, translate_function, env_name)
            latex = process_latex.process_specific_env(latex, translate_function, env_name + r'\*')

        # Process commands
        for command_name in all_commands:
            latex = process_latex.process_specific_command(latex, translate_function, command_name)
            latex = process_latex.process_specific_command(latex, translate_function, command_name + r'\*')

        # Process multi-argument commands
        for command_group in config.mularg_command_list:
            latex = process_latex.process_mularg_command(latex, translate_function, command_group)

        return latex

    def translate_text_in_paragraph_latex_and_leading_brace(self, latex_original_paragraph):
        # it acts recursively, i.e. it also translates braces inside braces
        latex_translated_paragraph = self.translate_text_in_paragraph_latex(latex_original_paragraph)
        latex_translated_paragraph = process_latex.process_leading_level_brace(latex_translated_paragraph, self.translate_text_in_paragraph_latex_and_leading_brace)
        return latex_translated_paragraph

    def translate_paragraph_latex(self, latex_original_paragraph):
        latex_translated_paragraph = self.translate_text_in_paragraph_latex_and_leading_brace(latex_original_paragraph)
        latex_translated_paragraph = self.translate_latex_all_objects(latex_translated_paragraph)
        return latex_translated_paragraph

    def split_latex_to_paragraphs(self, latex):
        '''
        1. convert latex to text and objects
        2. split text
        3. convert text back to objects
        '''
        text, objs = process_latex.replace_latex_objects(latex)
        paragraphs_text = re.split(r'\n\n+', text)
        paragraphs_latex = [process_latex.recover_latex_objects(paragraph_text, objs)[0] for paragraph_text in paragraphs_text]
        return paragraphs_latex

    def worker(self, latex_original_paragraph):
        try:
            # Check for problematic LaTeX patterns that might cause issues
            if '\\string@' in latex_original_paragraph:
                print(f"Warning: Found problematic \\string@ pattern in paragraph {self.num}, cleaning...")
                # Replace problematic patterns
                latex_original_paragraph = latex_original_paragraph.replace('\\string@', ' @')

            if self.add_cache:
                hash_key_paragraph = cache.deterministic_hash(latex_original_paragraph)
                latex_translated_paragraph = cache.load_paragraph(self.hash_key, hash_key_paragraph)
                if latex_translated_paragraph is None:
                    latex_translated_paragraph = self.translate_paragraph_latex(latex_original_paragraph)
                    cache.write_paragraph(self.hash_key, hash_key_paragraph, latex_translated_paragraph)
            else:
                latex_translated_paragraph = self.translate_paragraph_latex(latex_original_paragraph)
            self.num += 1
            return latex_translated_paragraph
        except BaseException as e:
            print(f'Error found in Paragraph {self.num}')
            print(f'Error type: {type(e).__name__}')
            print(f'Error message: {str(e)}')
            print(f'Content preview: {latex_original_paragraph[:100] + "..." if len(latex_original_paragraph) > 100 else latex_original_paragraph}')
            # Return original paragraph instead of raising exception to prevent translation from stopping
            print('Returning original paragraph to continue translation...')
            return latex_original_paragraph
        except Exception as e:
            print(f'Unexpected error in Paragraph {self.num}: {e}')
            return latex_original_paragraph

    def translate_full_latex(self, latex_original, make_complete=True, nocache=False):
        self.add_cache = (not nocache)
        if self.add_cache:
            cache.remove_extra()
            self.hash_key = cache.deterministic_hash((latex_original, __version__, self.translator.engine, self.translator.language_from, self.translator.language_to, config.mularg_command_list))
            if cache.is_cached(self.hash_key):
                print('Cache is found')
            cache.create_cache(self.hash_key)

        self.nbad = 0
        self.ntotal = 0

        latex_original = process_latex.remove_tex_comments(latex_original)
        latex_original = latex_original.replace(r'\mathbf', r'\boldsymbol')
        # \bibinfo {note} is not working in xelatex
        latex_original = process_latex.remove_bibnote(latex_original)
        latex_original = process_latex.process_newcommands(latex_original)

        # Protect makeatletter blocks to prevent translation of @ commands
        latex_original, protected_blocks = process_latex.process_makeatletter_blocks(latex_original)

        latex_original = process_latex.replace_accent(latex_original)
        latex_original = process_latex.replace_special(latex_original)

        self.complete = process_latex.is_complete(latex_original)
        self.theorems = process_latex.get_theorems(latex_original)
        if self.complete:
            print('It is a full latex document')
            latex_original, tex_begin, tex_end = process_latex.split_latex_document(latex_original, r'\begin{document}', r'\end{document}')
            tex_begin = process_latex.remove_blank_lines(tex_begin)
            tex_begin = process_latex.insert_macro(tex_begin, '\\usepackage{xeCJK}\n\\usepackage{amsmath}')
        else:
            print('It is not a full latex document')
            latex_original = process_text.connect_paragraphs(latex_original)
            if make_complete:
                tex_begin = default_begin
                tex_end = default_end
            else:
                tex_begin = ''
                tex_end = ''

        latex_original_paragraphs = self.split_latex_to_paragraphs(latex_original)
        latex_translated_paragraphs = []
        self.num = 0
        # tqdm with concurrent.futures.ThreadPoolExecutor() and timeout handling
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Use submit with timeout instead of map to prevent hanging
            future_to_index = {executor.submit(self.worker, paragraph): i for i, paragraph in enumerate(latex_original_paragraphs)}
            latex_translated_paragraphs = [None] * len(latex_original_paragraphs)
            completed_count = 0

            # Process all futures with better error handling
            all_futures = list(future_to_index.keys())

            # First, try to complete all futures
            for future in tqdm.auto.tqdm(concurrent.futures.as_completed(all_futures, timeout=600), total=len(latex_original_paragraphs)):
                try:
                    result = future.result(timeout=60)  # 60 seconds timeout per paragraph
                    index = future_to_index[future]
                    latex_translated_paragraphs[index] = result
                    completed_count += 1
                except concurrent.futures.TimeoutError:
                    print(f"Warning: Paragraph {future_to_index[future]} translation timed out, using original text")
                    index = future_to_index[future]
                    latex_translated_paragraphs[index] = latex_original_paragraphs[index]
                    completed_count += 1
                except Exception as e:
                    print(f"Warning: Paragraph {future_to_index[future]} translation failed: {e}, using original text")
                    index = future_to_index[future]
                    latex_translated_paragraphs[index] = latex_original_paragraphs[index]
                    completed_count += 1

            # After as_completed, check for any futures that didn't complete
            remaining_futures = [f for f in all_futures if not f.done()]
            if remaining_futures:
                print(f"Warning: {len(remaining_futures)} futures did not complete, processing with fallback...")
                for future in remaining_futures:
                    try:
                        # Try to get result with shorter timeout
                        result = future.result(timeout=10)
                        index = future_to_index[future]
                        latex_translated_paragraphs[index] = result
                        completed_count += 1
                    except Exception as e:
                        print(f"Warning: Fallback failed for paragraph {future_to_index[future]}: {e}")
                        index = future_to_index[future]
                        latex_translated_paragraphs[index] = latex_original_paragraphs[index]
                        completed_count += 1

        # Check for any None values and fill with original text
        none_count = latex_translated_paragraphs.count(None)
        if none_count > 0:
            print(f"Warning: {none_count} paragraphs were not translated, filling with original text")
            for i, paragraph in enumerate(latex_translated_paragraphs):
                if paragraph is None:
                    latex_translated_paragraphs[i] = latex_original_paragraphs[i]

        print(f"Translation summary: {completed_count}/{len(latex_original_paragraphs)} paragraphs processed")

        latex_translated = '\n\n'.join(latex_translated_paragraphs)

        latex_translated = tex_begin + '\n' + latex_translated + '\n' + tex_end

        # Title is probably outside the body part
        self.num = 'title'
        latex_translated = process_latex.process_specific_command(latex_translated, self.translate_text_in_paragraph_latex, 'title')

        latex_translated = latex_translated.replace('%', '\\%')

        # Recover protected makeatletter blocks (must be done before recovering special characters)
        latex_translated = process_latex.recover_makeatletter_blocks(latex_translated, protected_blocks)

        latex_translated = process_latex.recover_special(latex_translated)
        latex_translated = process_latex.recover_accent(latex_translated)

        # ENHANCED: Fix bibliography formatting issues
        # This addresses double backslashes, spaces after backslashes, extra spaces in braces, etc.
        def fix_bibliography_formatting(text):
            """Fix bibliography formatting issues in LaTeX text."""
            # Fix double backslash issues
            text = re.sub(r'\\\\(bibliographystyle|bibliography)', r'\\\1', text)
            # Also handle the case where we have space + double backslash
            text = re.sub(r'\\ \\(bibliographystyle|bibliography)', r'\\\1', text)

            # Fix spaces after backslashes
            text = re.sub(r'\\\s+(bibliographystyle|bibliography)', r'\\\1', text)
            text = re.sub(r'\\ (bibliographystyle|bibliography)', r'\\\1', text)

            # Fix missing backslashes on bibliography commands
            text = re.sub(r'(?<!\\)(bibliographystyle|bibliography)(?=\s*\{)', r'\\\1', text)

            # Fix extra spaces inside braces for bibliography commands
            text = re.sub(r'(\\(?:bibliographystyle|bibliography)\s*\{)\s*([^}]+?)\s*(\})',
                          lambda m: m.group(1) + m.group(2).strip() + m.group(3), text)

            # Remove duplicate bibliography commands (keep first occurrence)
            lines = text.split('\n')
            seen_commands = set()
            cleaned_lines = []

            for line in lines:
                # Check if this line contains a bibliography command
                if re.search(r'\\(?:bibliographystyle|bibliography)\s*\{[^}]*\}', line):
                    # Extract the command and its argument
                    match = re.search(r'\\(bibliographystyle|bibliography)\s*\{([^}]*)\}', line)
                    if match:
                        command = match.group(1)
                        argument = match.group(2)
                        command_key = f"{command}:{argument}"

                        # Only keep the first occurrence
                        if command_key not in seen_commands:
                            seen_commands.add(command_key)
                            cleaned_lines.append(line)
                        # Skip duplicates
                        continue

                # Keep non-bibliography lines
                cleaned_lines.append(line)

            return '\n'.join(cleaned_lines)

        latex_translated = fix_bibliography_formatting(latex_translated)

        # Remove duplicate bibliography commands (keep first occurrence)
        def remove_duplicate_bibliography_commands(text):
            """Remove duplicate bibliography commands, keeping only the first occurrence."""
            lines = text.split('\n')
            seen_commands = set()
            cleaned_lines = []

            for line in lines:
                # Check if this line contains a bibliography command
                if re.search(r'\\(?:bibliographystyle|bibliography)\s*\{[^}]*\}', line):
                    # Extract the command and its argument
                    match = re.search(r'\\(bibliographystyle|bibliography)\s*\{([^}]*)\}', line)
                    if match:
                        command = match.group(1)
                        argument = match.group(2)
                        command_key = f"{command}:{argument}"

                        # Only keep the first occurrence
                        if command_key not in seen_commands:
                            seen_commands.add(command_key)
                            cleaned_lines.append(line)
                        # Skip duplicates
                        continue

                # Keep non-bibliography lines
                cleaned_lines.append(line)

            return '\n'.join(cleaned_lines)

        latex_translated = remove_duplicate_bibliography_commands(latex_translated)

        # ENHANCED: Fix color model translation issues
        def fix_color_model_translation(text):
            """Fix color model names that were incorrectly translated with spaces"""
            # Fix RGB color model - remove extra spaces that were added during translation
            text = re.sub(r'\{\s*RGB\s*\}', '{RGB}', text)

            # Fix HTML color model
            text = re.sub(r'\{\s*HTML\s*\}', '{HTML}', text)

            # Fix other color models that might have been affected
            color_models = ['RGB', 'CMYK', 'HSB', 'HSL', 'Gray', 'wave']
            for model in color_models:
                # Match translated model names with spaces around them
                pattern = rf'\{{\s*{model}\s*\}}'
                replacement = f'{{{model}}}'
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

            # Fix color values that have extra spaces
            text = re.sub(r'\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}', r'{\1,\2,\3}', text)

            # Fix HTML color values with extra spaces
            text = re.sub(r'\{\s*([A-F0-9]+)\s*\}', r'{\1}', text)

            return text

        latex_translated = fix_color_model_translation(latex_translated)

        # Optimize table widths to prevent overflow
        try:
            from table_optimizer import optimize_all_tables
            latex_translated = optimize_all_tables(latex_translated)
            print('Table width optimization completed')
        except ImportError as e:
            print(f'Warning: Table optimizer not available: {e}')
        except Exception as e:
            print(f'Warning: Table optimization failed: {e}')

        self.close()

        print(self.ntotal - self.nbad, '/',  self.ntotal, 'latex object are correctly translated')

        return latex_translated


def translate_single_tex_file(input_path, output_path, engine, l_from, l_to, debug, nocache, threads):
    # Display translation engine information
    import os
    filename = os.path.basename(input_path)
    print(f'Processing {filename} using {engine.upper()} translation engine...')

    text_translator = TextTranslator(engine, l_to, l_from)
    latex_translator = LatexTranslator(text_translator, debug, threads)

    input_encoding = get_file_encoding(input_path)
    text_original = open(input_path, encoding=input_encoding).read()
    text_final = latex_translator.translate_full_latex(text_original, nocache=nocache)
    with open(output_path, "w", encoding='utf-8') as file:
        print(text_final, file=file)
    print('Number of translation called:', text_translator.number_of_calls)
    print('Total characters translated:', text_translator.tot_char)
    print('saved to', output_path)
