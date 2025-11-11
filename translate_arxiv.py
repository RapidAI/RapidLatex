import utils
import process_latex
import process_file
from translate import translate_single_tex_file
from encoding import get_file_encoding
import appdata
app_paths = appdata.AppDataPaths('mathtranslate')
app_dir = app_paths.app_data_path
import os
import sys
import shutil
import gzip
import zipfile
import tarfile
import tempfile
import urllib.request
import socket
import time
import subprocess


def check_network_connectivity(timeout=10):
    """
    Check if network connectivity is available and ArXiv is accessible
    """
    try:
        # Basic connectivity check
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        print("[OK] Network connectivity confirmed")

        # Check ArXiv accessibility
        import urllib.request
        req = urllib.request.Request('https://arxiv.org/',
                                   headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.getcode() == 200:
                print("[OK] ArXiv server accessible")
                return True

    except socket.gaierror:
        print("[ERROR] DNS resolution failed - check your internet connection")
    except socket.timeout:
        print("[ERROR] Network timeout - check your internet connection")
    except urllib.error.URLError as e:
        print(f"[ERROR] ArXiv server inaccessible: {e}")
    except Exception as e:
        print(f"[ERROR] Network connectivity check failed: {e}")

    return False


def download_source(number, path, max_retries=3, timeout=60):
    """
    Download ArXiv source with retry mechanism and improved error handling
    """
    url = f'https://arxiv.org/e-print/{number}'
    print(f'Downloading from {url}')

    # Quick network connectivity check before starting download
    # Note: This check can be skipped if the function is called with a custom implementation

    for attempt in range(max_retries):
        try:
            # Use a more robust download method with timeout
            import urllib.request
            import urllib.error

            # Create request with headers
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/x-tar, application/octet-stream, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                }
            )

            # Download with timeout
            with urllib.request.urlopen(req, timeout=timeout) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0

                with open(path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Show progress for large files
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if attempt == 0:  # Only show progress on first attempt
                                print(f'\rDownload progress: {progress:.1f}%', end='', flush=True)

                if attempt == 0:
                    print()  # New line after progress

            # Verify the downloaded file
            if os.path.exists(path) and os.path.getsize(path) > 0:
                print(f'Successfully downloaded {number} ({os.path.getsize(path)} bytes)')
                return True
            else:
                raise Exception("Downloaded file is empty or missing")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f'Error: ArXiv paper {number} not found (404)')
                raise Exception(f"ArXiv paper {number} does not exist")
            elif e.code == 403:
                print(f'Error: Access forbidden (403) - attempt {attempt + 1}/{max_retries}')
            elif e.code >= 500:
                print(f'Server error ({e.code}) - attempt {attempt + 1}/{max_retries}')
            else:
                print(f'HTTP error ({e.code}) - attempt {attempt + 1}/{max_retries}')

        except urllib.error.URLError as e:
            if isinstance(e.reason, OSError) and 'timed out' in str(e.reason):
                print(f'Download timeout - attempt {attempt + 1}/{max_retries}')
            else:
                print(f'Network error: {e.reason} - attempt {attempt + 1}/{max_retries}')

        except Exception as e:
            print(f'Download error: {e} - attempt {attempt + 1}/{max_retries}')

        # Clean up partial download on failure
        if os.path.exists(path):
            os.remove(path)

        if attempt < max_retries - 1:
            # Exponential backoff
            wait_time = min(2 ** attempt, 30)  # Max 30 seconds
            print(f'Retrying in {wait_time} seconds...')
            import time
            time.sleep(wait_time)
        else:
            raise Exception(f"Failed to download ArXiv {number} after {max_retries} attempts")

    return False


def download_source_with_cache(number, path, force_download=False):
    """
    Download ArXiv source with intelligent caching and integrity verification
    """
    # Create input directory for storing downloaded arxiv documents (in project root)
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, 'input')
    os.makedirs(input_dir, exist_ok=True)

    # Store original arxiv document in input directory
    arxiv_filename = f"{number.replace('/', '-')}.tar.gz"
    input_path = os.path.join(input_dir, arxiv_filename)

    # Check if we should use cached file
    use_cache = not force_download and os.path.exists(input_path)

    if use_cache:
        print(f'Checking cached file: {input_path}')

        # Verify cached file integrity
        if verify_download_integrity(input_path):
            print(f'Using valid cached download from: {input_path}')
            try:
                shutil.copyfile(input_path, path)
                return True
            except Exception as e:
                print(f'Warning: Failed to copy cached file: {e}')
                print('Will re-download the file')
                use_cache = False
        else:
            print(f'Cached file appears corrupted, will re-download')
            # Remove corrupted cache file
            try:
                os.remove(input_path)
                print(f'Removed corrupted cached file: {input_path}')
            except Exception as e:
                print(f'Warning: Could not remove corrupted cache file: {e}')
            use_cache = False

    if not use_cache:
        try:
            # Download to temporary location first
            temp_path = path + '.tmp'
            download_source(number, temp_path)

            # Verify the downloaded file
            if verify_download_integrity(temp_path):
                # Move to final locations
                shutil.move(temp_path, path)
                shutil.copyfile(path, input_path)
                print(f'Downloaded source saved to: {input_path}')
                return True
            else:
                os.remove(temp_path)
                raise Exception("Downloaded file failed integrity check")

        except Exception as e:
            # Clean up any partial downloads
            temp_path = path + '.tmp'
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

    return False


def verify_download_integrity(file_path):
    """
    Verify the integrity of a downloaded ArXiv file
    """
    if not os.path.exists(file_path):
        return False

    file_size = os.path.getsize(file_path)

    # File should be at least 1KB and not corrupted
    if file_size < 1024:
        print(f'Warning: Downloaded file too small ({file_size} bytes)')
        return False

    # Check if it's a valid gzip/tar file
    try:
        # Try to read gzip header
        with open(file_path, 'rb') as f:
            header = f.read(2)
            if len(header) < 2 or header != b'\x1f\x8b':  # gzip magic number
                # Not a gzip file, might be plain text or PDF
                return True

        # For gzip files, try to decompress a small portion
        import gzip
        with gzip.open(file_path, 'rb') as f:
            # Try to read first 1KB to verify it's valid
            f.read(1024)

        print(f'File integrity verified: {file_path} ({file_size} bytes)')
        return True

    except gzip.BadGzipFile:
        print(f'Warning: File appears to be corrupted gzip: {file_path}')
        return False
    except EOFError:
        print(f'Warning: Incomplete gzip file: {file_path}')
        return False
    except Exception as e:
        print(f'Warning: Error verifying file {file_path}: {e}')
        return False


def process_local_archive(archive_path, temp_dir):
    """
    Process local archive file (zip, tar.gz, etc.) and extract to temp directory
    Returns True if successful, False otherwise
    """
    print(f'Processing local archive: {archive_path}')

    if not os.path.exists(archive_path):
        print(f'ERROR: Archive file not found: {archive_path}')
        return False

    try:
        if archive_path.lower().endswith('.zip'):
            print('Extracting ZIP archive...')
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            print(f'Successfully extracted ZIP archive to {temp_dir}')
            return True

        elif archive_path.lower().endswith('.tar.gz') or archive_path.lower().endswith('.tgz'):
            print('Extracting TAR.GZ archive...')
            import tarfile
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(temp_dir)
            print(f'Successfully extracted TAR.GZ archive to {temp_dir}')
            return True

        elif archive_path.lower().endswith('.tar'):
            print('Extracting TAR archive...')
            import tarfile
            with tarfile.open(archive_path, 'r') as tar_ref:
                tar_ref.extractall(temp_dir)
            print(f'Successfully extracted TAR archive to {temp_dir}')
            return True

        elif archive_path.lower().endswith('.tar.bz2') or archive_path.lower().endswith('.tbz2'):
            print('Extracting TAR.BZ2 archive...')
            import tarfile
            with tarfile.open(archive_path, 'r:bz2') as tar_ref:
                tar_ref.extractall(temp_dir)
            print(f'Successfully extracted TAR.BZ2 archive to {temp_dir}')
            return True

        elif archive_path.lower().endswith('.tar.xz') or archive_path.lower().endswith('.txz'):
            print('Extracting TAR.XZ archive...')
            import tarfile
            with tarfile.open(archive_path, 'r:xz') as tar_ref:
                tar_ref.extractall(temp_dir)
            print(f'Successfully extracted TAR.XZ archive to {temp_dir}')
            return True

        else:
            print(f'ERROR: Unsupported archive format: {archive_path}')
            print('Supported formats: .zip, .tar.gz, .tgz, .tar, .tar.bz2, .tbz2, .tar.xz, .txz')
            return False

    except Exception as e:
        print(f'ERROR: Failed to extract archive {archive_path}: {e}')
        return False


def is_local_archive(input_str):
    """
    Check if input string refers to a local archive file
    Returns the archive path if it's a local file, None otherwise
    """
    # Remove quotes if present
    input_str = input_str.strip('"\'')

    # Check if it's a file path
    if os.path.isfile(input_str):
        # Check if it has supported archive extension
        supported_extensions = ['.zip', '.tar.gz', '.tgz', '.tar', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']
        for ext in supported_extensions:
            if input_str.lower().endswith(ext):
                return input_str
    return None


def is_local_directory(input_str):
    """
    Check if input string refers to a local directory
    Returns the directory path if it's a valid directory, None otherwise
    """
    # Remove quotes if present
    input_str = input_str.strip('"\'')

    # Check if it's a directory path
    if os.path.isdir(input_str):
        return input_str
    return None


def is_pdf(filename):
    return open(filename, 'rb').readline()[0:4] == b'%PDF'


def fallback_compilation(document_dir, tex_filename, document_name, output_dir):
    """Fallback compilation method using basic XeLaTeX with proper bibliography handling"""
    print(f'Using fallback compilation for {tex_filename}...')

    # Change to document directory for compilation
    original_cwd = os.getcwd()
    os.chdir(document_dir)

    # Check if .bib files exist
    has_bib_files = len([f for f in os.listdir('.') if f.endswith('.bib')]) > 0

    try:
        # First, clean any previous compilation files to avoid issues
        clean_files = [
            f"{os.path.splitext(tex_filename)[0]}.aux",
            f"{os.path.splitext(tex_filename)[0]}.blg",
            f"{os.path.splitext(tex_filename)[0]}.log",
            f"{os.path.splitext(tex_filename)[0]}.toc",
            f"{os.path.splitext(tex_filename)[0]}.out"
        ]
        # Only clean .bbl if we have .bib files (will generate new one)
        if has_bib_files:
            clean_files.append(f"{os.path.splitext(tex_filename)[0]}.bbl")

        for f in clean_files:
            if os.path.exists(f):
                os.remove(f)
                print(f"Cleaned old compilation file: {os.path.basename(f)}")

        # Set up variables for compilation attempts and timeouts
        xelatex_cmd_base = ['xelatex', '-interaction=nonstopmode', '-halt-on-error']
        bibtex_cmd_base = ['bibtex', f'{os.path.splitext(tex_filename)[0]}.aux']

        try:
            # Step 1: First xelatex run (generates .aux file with citation info)
            print('Running xelatex (1/3)...')
            result1 = subprocess.run(
                xelatex_cmd_base + ['-no-pdf', tex_filename],
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300
            )

            # Step 2: Run bibtex if .bib files exist and .aux file was generated
            result_bib = None
            aux_filename = f'{os.path.splitext(tex_filename)[0]}.aux'
            if has_bib_files and os.path.exists(aux_filename):
                print('Running bibtex...')
                result_bib = subprocess.run(
                    bibtex_cmd_base,
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=120
                )
                if result_bib.returncode != 0:
                    print(f'Warning: bibtex returned non-zero exit code')
                    if result_bib.stderr:
                        print(f'Bibtex errors: {result_bib.stderr[-200:]}')
            elif has_bib_files:
                print(f'Warning: Could not run bibtex - no .aux file generated by first xelatex run')

            # Step 3: Second xelatex run (inserts bibliography and resolves references)
            print('Running xelatex (2/3)...')
            result2 = subprocess.run(
                xelatex_cmd_base + [tex_filename],
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300
            )

            # Step 4: Final xelatex run (updates reference numbers)
            print('Running xelatex (3/3)...')
            result3 = subprocess.run(
                xelatex_cmd_base + [tex_filename],
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300
            )
        except subprocess.TimeoutExpired:
            print(f'Error: LaTeX compilation timed out after 5 minutes per run')
            return False
        except Exception as e:
            print(f'Error: Unexpected error during compilation: {e}')
            return False

        # Check results
        if all(r.returncode == 0 for r in [result1, result2, result3]):
            print(f'Fallback compilation successful: {tex_filename}')
            pdf_filename = os.path.splitext(tex_filename)[0] + '.pdf'
            if os.path.exists(pdf_filename):
                print(f'PDF generated: {pdf_filename}')
                # Copy PDF to output directory with document name
                pdf_source_path = os.path.join(document_dir, pdf_filename)
                pdf_output_name = f"{document_name}.pdf"
                pdf_output_path = os.path.join(output_dir, pdf_output_name)
                shutil.copy2(pdf_source_path, pdf_output_path)
                print(f'PDF copied to: {pdf_output_path}')
            else:
                print(f'Fallback compilation completed but PDF not found: {pdf_filename}')
        else:
            print(f'Fallback compilation warnings or errors for {tex_filename}:')
            print(f'Run 1 return code: {result1.returncode}')
            if result2:
                print(f'Run 2 return code: {result2.returncode}')
            if result3:
                print(f'Run 3 return code: {result3.returncode}')

    except Exception as e:
        print(f'Fallback compilation error for {tex_filename}: {e}')
    finally:
        os.chdir(original_cwd)

def list_input_files():
    """List all downloaded arxiv files in input directory"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, 'input')
    if os.path.exists(input_dir):
        files = [f for f in os.listdir(input_dir) if f.endswith('.tar.gz')]
        if files:
            print(f'Arxiv files in input directory ({input_dir}):')
            for file in sorted(files):
                file_path = os.path.join(input_dir, file)
                size = os.path.getsize(file_path)
                print(f'  {file} ({size} bytes)')
        else:
            print('No arxiv files found in input directory')
    else:
        print('Input directory does not exist')


def clean_input_files():
    """Clean all files in input directory"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, 'input')
    if os.path.exists(input_dir):
        files = [f for f in os.listdir(input_dir) if f.endswith('.tar.gz')]
        if files:
            for file in files:
                file_path = os.path.join(input_dir, file)
                os.remove(file_path)
                print(f'Removed: {file_path}')
            print(f'Cleaned {len(files)} files from input directory')
        else:
            print('No files to clean in input directory')
    else:
        print('Input directory does not exist')


def verify_cached_files():
    """Verify integrity of all cached ArXiv files"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, 'input')

    if not os.path.exists(input_dir):
        print('Input directory does not exist')
        return

    files = [f for f in os.listdir(input_dir) if f.endswith('.tar.gz')]
    if not files:
        print('No cached ArXiv files found')
        return

    print(f'Verifying {len(files)} cached ArXiv files...')
    valid_files = 0
    corrupted_files = 0

    for file in files:
        file_path = os.path.join(input_dir, file)
        print(f'\nVerifying: {file}')

        if verify_download_integrity(file_path):
            print(f'  [OK] Valid')
            valid_files += 1
        else:
            print(f'  [ERROR] Corrupted')
            corrupted_files += 1

            # Ask user if they want to remove corrupted files
            try:
                response = input(f'Remove corrupted file {file}? (y/N): ').strip().lower()
                if response in ['y', 'yes']:
                    os.remove(file_path)
                    print(f'  Removed corrupted file: {file}')
            except (KeyboardInterrupt, EOFError):
                print('\nSkipping file removal')

    print(f'\nVerification complete:')
    print(f'  Valid files: {valid_files}')
    print(f'  Corrupted files: {corrupted_files}')


def get_download_stats():
    """Get statistics about downloaded ArXiv files"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(project_root, 'input')

    if not os.path.exists(input_dir):
        return {'total_files': 0, 'total_size': 0, 'files': []}

    files = [f for f in os.listdir(input_dir) if f.endswith('.tar.gz')]
    total_size = sum(os.path.getsize(os.path.join(input_dir, f)) for f in files)

    return {
        'total_files': len(files),
        'total_size': total_size,
        'files': sorted(files)
    }


def loop_files(dir):
    all_files = []
    for root, dirs, files in os.walk(dir):
        for file in files:
            all_files.append(os.path.join(root, file))
    return all_files


def zipdir(dir, output_path):
    # ziph is zipfile handle
    zipf = zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED)
    for file in loop_files(dir):
        rel_path = os.path.relpath(file, dir)
        zipf.write(file, arcname=rel_path)


def translate_dir(dir, options):
    files = loop_files(dir)
    texs = [f[0:-4] for f in files if f[-4:] == '.tex']
    bibs = [f[0:-4] for f in files if f[-4:] == '.bib']
    bbls = [f[0:-4] for f in files if f[-4:] == '.bbl']
    print('main tex files found:')
    complete_texs = []
    for tex in texs:
        path = f'{tex}.tex'
        input_encoding = get_file_encoding(path)
        content = open(path, encoding=input_encoding).read()
        content = process_latex.remove_tex_comments(content)
        complete = process_latex.is_complete(content)
        if complete:
            print(path)
            process_file.merge_complete(tex)
            # Always use .bbl files if available (they contain formatted bibliography)
            # But not if there are .bib files (we want to generate fresh references)
            if tex in bbls and not bibs:
                process_file.add_bbl(tex)
            complete_texs.append(tex)

    # Check for .bib files
    if len(complete_texs) > 0 and len(bibs) > 0:
        print(f'Found {len(bibs)} .bib files: {[f+".bib" for f in bibs]}')
        print('References will be processed by LaTeX during compilation')
        # Ensure \bibliographystyle command exists for each tex file
        for tex in complete_texs:
            tex_path = f'{tex}.tex'
            process_file.ensure_bibliographystyle(tex_path)
    if len(complete_texs) == 0:
        return False
    for basename in texs:
        if basename in complete_texs:
            continue
        os.remove(f'{basename}.tex')
    # Only remove .bbl files that don't match the complete tex files
    for basename in bbls:
        if basename not in complete_texs:
            os.remove(f'{basename}.bbl')
    if options.notranslate:
        return complete_texs
    for filename in complete_texs:
        print(f'Processing {filename} using {options.engine.upper()} translation engine')
        file_path = f'{filename}.tex'
        translate_single_tex_file(file_path, file_path, options.engine, options.l_from, options.l_to, options.debug, options.nocache, options.threads)

    # After translation, ensure \bibliographystyle exists if .bib files are present
    if len(bibs) > 0:
        for tex in complete_texs:
            tex_path = f'{tex}.tex'
            process_file.ensure_bibliographystyle(tex_path)

    return complete_texs


def main(args=None, require_updated=False):
    '''
    There are four types of a downdload arxiv project
    1. It is simply a PDF file (cannot translate)
    2. It is a gzipped text file, but the text file contains nothing meaningful (cannot translate)
    3. It is a gzipped tex file (can translate)
    4. It is a gzipped + tarzipped tex project (can translate)

    return False for the first two cases
    return True if the translation is successful (last two cases)

    to call this function from python,
    you can do e.g `main(['2205.15510', '-o', 'output.zip'])`
    '''
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("number", nargs='?', type=str, help='arxiv number, local directory path, or path to local archive file (.zip, .tar.gz, .tgz, .tar, .tar.bz2, .tbz2, .tar.xz, .txz)')
    parser.add_argument("-o", type=str, help='output path')
    parser.add_argument("--from_dir", action='store_true')
    parser.add_argument("--notranslate", action='store_true')  # debug option
    parser.add_argument("--compile", action='store_true', default=True, help='compile the main LaTeX file after translation (default: enabled)')
    parser.add_argument("--no-compile", action='store_true', help='disable automatic compilation')
    parser.add_argument("--list-input", action='store_true', help='list all downloaded arxiv files in input directory')
    parser.add_argument("--clean-input", action='store_true', help='clean all files in input directory')
    parser.add_argument("--no-network-check", action='store_true', help='skip network connectivity check before downloading')
    parser.add_argument("--verify-cache", action='store_true', help='verify integrity of cached ArXiv files')
    utils.add_arguments(parser)
    options = parser.parse_args(args)
    utils.process_options(options)

    # Handle input directory management options (skip version check for these)
    if options.list_input:
        list_input_files()
        sys.exit(0)

    if options.clean_input:
        clean_input_files()
        sys.exit(0)

    if options.verify_cache:
        verify_cached_files()
        sys.exit(0)

    # Only check for updates if doing actual translation work and network check is not disabled
    try:
        if not hasattr(options, 'no_network_check') or not options.no_network_check:
            utils.check_update(require_updated=require_updated)
    except Exception:
        print("Warning: Could not check for updates (network error). Continuing anyway...")

    # Handle compile options: if --no-compile is specified, disable compilation
    if hasattr(options, 'no_compile') and options.no_compile:
        options.compile = False

    if options.number is None:
        parser.print_help()
        sys.exit()

    number = options.number

    # Check if input is a local archive file
    local_archive = is_local_archive(number)
    local_directory = is_local_directory(number)

    if local_archive:
        print(f'Using local archive: {local_archive}')
        print()
        # Use archive filename (without extension) as document name
        document_name = os.path.splitext(os.path.basename(local_archive))[0]
        print(f'Document name: {document_name}')
    elif local_directory:
        print(f'Using local directory: {local_directory}')
        print()
        # Use directory name as document name
        document_name = os.path.basename(local_directory.rstrip('/\\'))
        print(f'Document name: {document_name}')
    else:
        print('arxiv number:', number)
        print()
        # Original arxiv processing
        document_name = number.replace('/', '-')  # Use arxiv ID as document name

    download_path = document_name

    # Create output directory
    output_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Create document-specific directory in output folder
    if options.from_dir:
        document_name = os.path.basename(number.rstrip('/\\'))

    document_dir = os.path.join(output_dir, document_name)
    os.makedirs(document_dir, exist_ok=True)

    if options.o is None:
        output_path = os.path.join(document_dir, f'{download_path}.zip')
    else:
        # If custom output path is provided, also put it in document directory
        if not os.path.isabs(options.o):
            output_path = os.path.join(document_dir, options.o)
        else:
            output_path = options.o

    success = True
    main_tex_files = False
    cwd = os.getcwd()

    # Create temporary directory within document directory
    import time
    import random
    temp_dir_name = f"temp_{int(time.time())}_{random.randint(1000, 9999)}"
    temp_dir = os.path.join(document_dir, temp_dir_name)
    os.makedirs(temp_dir, exist_ok=True)
    print(f'document directory: {document_dir}')
    print(f'temporary directory: {temp_dir}')

    try:
        if options.from_dir or local_directory:
            src_dir = local_directory if local_directory else number
            shutil.copytree(src_dir, temp_dir, dirs_exist_ok=True)
        os.chdir(temp_dir)
        # must os.chdir(cwd) whenever released!

        if not options.from_dir and not local_directory:
            if local_archive:
                # Process local archive file
                try:
                    extract_success = process_local_archive(local_archive, temp_dir)
                    if not extract_success:
                        print('Failed to extract local archive')
                        os.chdir(cwd)
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return False
                    # After successful extraction, process the directory
                    main_tex_files = translate_dir('.', options)
                except BaseException as e:
                    print(f'Error processing local archive: {e}')
                    os.chdir(cwd)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False
            else:
                # Original arxiv download logic
                try:
                    download_source_with_cache(number, download_path)
                except Exception as download_error:
                    print(f'Cannot download source for arXiv {number}: {download_error}')
                    print('Possible reasons:')
                    print('1. Network connectivity issues')
                    print('2. The arXiv paper does not have source files available')
                    print('3. The arXiv ID is incorrect or the paper does not exist')
                    print('4. arXiv servers are temporarily unavailable')

                    # Try to check if the paper exists by checking the abstract page
                    try:
                        import urllib.request
                        import urllib.error
                        test_url = f'https://arxiv.org/abs/{number}'
                        response = urllib.request.urlopen(test_url, timeout=10)
                        if response.getcode() == 200:
                            print(f'Note: The paper {number} exists, but source files may not be available for download.')
                            print('Some papers only have PDF files available without LaTeX source.')
                    except Exception as check_error:
                        print(f'Unable to verify if arXiv {number} exists: {check_error}')

                    os.chdir(cwd)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return False
                if is_pdf(download_path):
                    # case 1
                    success = False
                    main_tex_files = False
                else:
                    try:
                        content = gzip.decompress(open(download_path, "rb").read())
                        with open(download_path, "wb") as f:
                            f.write(content)
                    except (EOFError, gzip.BadGzipFile) as e:
                        print(f'Error: Corrupted gzip file detected: {e}')
                        print('Attempting to re-download the file...')
                        os.remove(download_path)
                        # Also remove the cached file
                        project_root = os.path.dirname(os.path.abspath(__file__))
                        input_dir = os.path.join(project_root, 'input')
                        arxiv_filename = f"{number.replace('/', '-')}.tar.gz"
                        cached_path = os.path.join(input_dir, arxiv_filename)
                        if os.path.exists(cached_path):
                            os.remove(cached_path)
                            print(f'Removed corrupted cached file: {cached_path}')

                        try:
                            # Download fresh copy bypassing cache
                            download_source_with_cache(number, download_path, force_download=True)
                            content = gzip.decompress(open(download_path, "rb").read())
                            with open(download_path, "wb") as f:
                                f.write(content)
                            print('Successfully re-downloaded and decompressed the file')
                        except Exception as e2:
                            print(f'Error: Failed to download or decompress file after retry: {e2}')
                            os.chdir(cwd)
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            return False
                    try:
                        # case 4
                        with tarfile.open(download_path, mode='r') as f:
                            f.extractall()
                        os.remove(download_path)
                    except tarfile.ReadError:
                        # case 2 or 3
                        print('This is a pure text file')
                        shutil.move(download_path, 'main.tex')
                main_tex_files = translate_dir('.', options)
        else:
            main_tex_files = translate_dir('.', options)

        # Handle the case where translate_dir returns False or a list of files
        if main_tex_files is False:
            success = False
        else:
            success = True

        os.chdir(cwd)
        if success:
            # case 3 or 4
            zipdir(temp_dir, output_path)

            # Compile LaTeX files if --compile option is used
            if options.compile and main_tex_files:
                print('\nCompiling LaTeX files...')

                # Copy all necessary files to document directory for compilation
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        source_file = os.path.join(root, file)
                        rel_path = os.path.relpath(source_file, temp_dir)
                        target_file = os.path.join(document_dir, rel_path)
                        # Create subdirectories if needed
                        target_dir = os.path.dirname(target_file)
                        if target_dir != document_dir:
                            os.makedirs(target_dir, exist_ok=True)
                        shutil.copy2(source_file, target_file)

                print(f'All files copied to document directory for compilation: {document_dir}')

                # Compile each main tex file using improved compilation script
                for tex_file in main_tex_files:
                    tex_filename = os.path.basename(tex_file) + '.tex'
                    tex_filepath = os.path.join(document_dir, tex_filename)
                    print(f'Compiling {tex_filename} with improved bibliography handling...')

                    try:
                        # Use our improved compilation script
                        import subprocess
                        import sys
                        project_root = os.path.dirname(os.path.abspath(__file__))
                        compile_script = os.path.join(project_root, 'compile_simple.py')

                        if os.path.exists(compile_script):
                            result = subprocess.run([
                                sys.executable, compile_script, tex_filepath
                            ], capture_output=True, text=True, encoding='utf-8', errors='ignore')

                            if result.returncode == 0:
                                print(f'Compiled successfully: {tex_filename}')
                                pdf_filename = os.path.splitext(tex_filename)[0] + '.pdf'
                                if os.path.exists(os.path.join(document_dir, pdf_filename)):
                                    print(f'PDF generated: {pdf_filename}')
                                    # Copy PDF to output directory with document name
                                    pdf_source_path = os.path.join(document_dir, pdf_filename)
                                    pdf_output_name = f"{document_name}.pdf"
                                    pdf_output_path = os.path.join(output_dir, pdf_output_name)
                                    shutil.copy2(pdf_source_path, pdf_output_path)
                                    print(f'PDF copied to: {pdf_output_path}')
                                else:
                                    print(f'Compilation completed but PDF not found: {pdf_filename}')
                            else:
                                print(f'Compilation failed for {tex_filename}:')
                                print(f'Error output: {result.stderr}')
                                # Fallback to simple compilation
                                fallback_compilation(document_dir, tex_filename, document_name, output_dir)
                        else:
                            print(f'Compilation script not found, using fallback method')
                            fallback_compilation(document_dir, tex_filename, document_name, output_dir)

                    except Exception as e:
                        print(f'Compilation error for {tex_filename}: {e}')
                        # Try fallback method
                        try:
                            fallback_compilation(document_dir, tex_filename, document_name, output_dir)
                        except:
                            print(f'Fallback compilation also failed for {tex_filename}')

    except BaseException as e:
        # first go back otherwise tempfile trying to delete the current directory that python is running in
        os.chdir(cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

    # Clean up temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    if success:
        print('zip file is saved to', output_path)
        print('You can upload the zip file to overleaf to autocompile')

        # Show input directory location
        project_root = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(project_root, 'input')

        if local_archive:
            # For local archives, show the original file path
            print(f'Original archive file: {local_archive}')
            print(f'Input directory: {input_dir}')
        else:
            # For arxiv downloads, show the cached file path
            arxiv_filename = f"{number.replace('/', '-')}.tar.gz"
            input_path = os.path.join(input_dir, arxiv_filename)
            print(f'Original arxiv source is saved to: {input_path}')
            print(f'Input directory: {input_dir}')

        return True
    else:
        if local_archive:
            print('Source code is not available for archive', local_archive)
        else:
            print('Source code is not available for arxiv', number)
        return False


if __name__ == "__main__":
    main()
