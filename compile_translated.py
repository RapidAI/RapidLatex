#!/usr/bin/env python
"""
编译翻译后的LaTeX文档的脚本
自动处理XeLaTeX兼容性和参考文献问题
"""

import os
import sys
import subprocess
import shutil

def compile_latex_document(tex_file_path, max_attempts=3):
    """
    编译LaTeX文档，自动处理XeLaTeX兼容性和参考文献

    Args:
        tex_file_path: LaTeX文件路径
        max_attempts: 最大编译尝试次数
    """
    # 获取文件目录和文件名
    tex_dir = os.path.dirname(os.path.abspath(tex_file_path))
    tex_name = os.path.splitext(os.path.basename(tex_file_path))[0]

    print(f"开始编译LaTeX文档: {tex_file_path}")
    print(f"工作目录: {tex_dir}")

    # 备份原始文件
    original_file = os.path.join(tex_dir, f"{tex_name}.tex")
    backup_file = os.path.join(tex_dir, f"{tex_name}.tex.backup")

    if os.path.exists(original_file):
        shutil.copy2(original_file, backup_file)
        print(f"已备份原始文件到: {backup_file}")

    try:
        # 修复XeLaTeX兼容性问题
        fix_xelatex_compatibility(original_file)

        # 执行完整的编译流程
        success = run_full_compilation_cycle(tex_dir, tex_name, max_attempts)

        if success:
            pdf_file = os.path.join(tex_dir, f"{tex_name}.pdf")
            if os.path.exists(pdf_file):
                print(f"✅ 编译成功！PDF文件已生成: {pdf_file}")
                return True
            else:
                print("❌ 编译完成但未找到PDF文件")
                return False
        else:
            print("❌ 编译失败")
            return False

    except Exception as e:
        print(f"❌ 编译过程中出现错误: {e}")
        return False

def fix_xelatex_compatibility(tex_file_path):
    """
    修复LaTeX文件以兼容XeLaTeX
    """
    print("正在修复XeLaTeX兼容性问题...")

    with open(tex_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除不兼容的命令和包
    modifications = [
        # 移除 \pdfoutput=1 命令
        (r'\pdfoutput=1\s*\n?', ''),
        # 移除 times 包（与XeLaTeX不兼容）
        (r'\\usepackage\{times\}\s*\n?', ''),
        # 移除 inputenc 包（XeLaTeX不需要）
        (r'\\usepackage\[utf8\]\{inputenc\}\s*\n?', ''),
        # 移除 fontenc 包（XeLaTeX不需要）
        (r'\\usepackage\[T1\]\{fontenc\}\s*\n?', ''),
    ]

    for pattern, replacement in modifications:
        if pattern in content:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            print(f"  - 移除了不兼容的命令/包: {pattern.strip()}")

    # 确保有 xeCJK 包
    if r'\usepackage{xeCJK}' not in content:
        # 在 documentclass 后添加 xeCJK
        content = re.sub(
            r'(\\documentclass[^}]*\})',
            r'\1\n\usepackage{xeCJK}',
            content
        )
        print("  - 添加了 xeCJK 包")

    # 写回文件
    with open(tex_file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("XeLaTeX兼容性修复完成")

def run_full_compilation_cycle(tex_dir, tex_name, max_attempts):
    """
    运行完整的LaTeX编译循环：XeLaTeX → BibTeX → XeLaTeX → XeLaTeX
    """
    import re

    print("开始编译循环...")

    for attempt in range(max_attempts):
        print(f"\n--- 编译尝试 {attempt + 1}/{max_attempts} ---")

        try:
            # 第一次 XeLaTeX 编译
            print("1. 运行第一次 XeLaTeX 编译...")
            result = subprocess.run(
                ['xelatex', f'{tex_name}.tex'],
                cwd=tex_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"   ❌ XeLaTeX 编译失败: {result.stderr}")
                continue

            print("   ✅ 第一次 XeLaTeX 编译完成")

            # 检查是否有 .bib 文件需要处理
            bib_file = os.path.join(tex_dir, 'references.bib')
            aux_file = os.path.join(tex_dir, f'{tex_name}.aux')

            if os.path.exists(bib_file) and os.path.exists(aux_file):
                # 检查 aux 文件中是否有 \bibdata 命令（表示有引用）
                with open(aux_file, 'r', encoding='utf-8') as f:
                    aux_content = f.read()

                if r'\bibdata' in aux_content:
                    print("2. 运行 BibTeX 处理参考文献...")
                    result = subprocess.run(
                        ['bibtex', tex_name],
                        cwd=tex_dir,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode == 0:
                        print("   ✅ BibTeX 处理完成")

                        # 第二次 XeLaTeX 编译
                        print("3. 运行第二次 XeLaTeX 编译...")
                        result = subprocess.run(
                            ['xelatex', f'{tex_name}.tex'],
                            cwd=tex_dir,
                            capture_output=True,
                            text=True,
                            timeout=120
                        )

                        if result.returncode == 0:
                            print("   ✅ 第二次 XeLaTeX 编译完成")

                            # 第三次 XeLaTeX 编译（确保所有引用正确解析）
                            print("4. 运行第三次 XeLaTeX 编译...")
                            result = subprocess.run(
                                ['xelatex', f'{tex_name}.tex'],
                                cwd=tex_dir,
                                capture_output=True,
                                text=True,
                                timeout=120
                            )

                            if result.returncode == 0:
                                print("   ✅ 第三次 XeLaTeX 编译完成")

                                # 检查是否还有未定义的引用
                                log_file = os.path.join(tex_dir, f'{tex_name}.log')
                                if os.path.exists(log_file):
                                    with open(log_file, 'r', encoding='utf-8') as f:
                                        log_content = f.read()

                                    # 检查是否有未定义的引用
                                    undefined_citations = re.findall(r"Citation `[^']+' on page \d+ undefined", log_content)
                                    undefined_references = re.findall(r"Reference `[^']+' on page \d+ undefined", log_content)

                                    if not undefined_citations and not undefined_references:
                                        print("   ✅ 所有引用都已正确解析")
                                        return True
                                    else:
                                        print(f"   ⚠️  仍有未定义的引用: {len(undefined_citations)} 个引用, {len(undefined_references)} 个参考文献")
                                        if attempt == max_attempts - 1:  # 最后一次尝试
                                            print("   ⚠️  继续使用当前结果")
                                            return True
                                else:
                                    print("   ✅ 编译完成（无法检查引用状态）")
                                    return True
                            else:
                                print(f"   ❌ 第三次 XeLaTeX 编译失败: {result.stderr}")
                        else:
                            print(f"   ❌ 第二次 XeLaTeX 编译失败: {result.stderr}")
                    else:
                        print(f"   ❌ BibTeX 处理失败: {result.stderr}")
                else:
                    print("   ℹ️  没有发现参考文献，跳过 BibTeX")
                    return True
            else:
                print("   ℹ️  没有找到参考文献文件，跳过 BibTeX")
                return True

        except subprocess.TimeoutExpired:
            print(f"   ❌ 编译超时")
            continue
        except Exception as e:
            print(f"   ❌ 编译过程中出现异常: {e}")
            continue

    return False

if __name__ == "__main__":
    import re

    if len(sys.argv) != 2:
        print("用法: python compile_translated.py <latex_file_path>")
        print("示例: python compile_translated.py output/2510.26037v1/main.tex")
        sys.exit(1)

    tex_file_path = sys.argv[1]

    if not os.path.exists(tex_file_path):
        print(f"❌ 文件不存在: {tex_file_path}")
        sys.exit(1)

    success = compile_latex_document(tex_file_path)
    sys.exit(0 if success else 1)