#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕文件重命名工具

该模块提供了一个函数，用于遍历目录并将 ASS 字幕文件重命名为与同目录下的 MKV 视频文件同名。
通过匹配文件名的季集格式（SxxEyy）来建立 ASS 和 MKV 文件之间的对应关系。

功能特点：
- 支持多种季集格式：SxxEyy, Sxx-Eyy, Sxx_Eyy, Sxx.Eyy, SxxEyy-Ezz 等
- 自动跳过隐藏目录
- 提供详细的操作日志和统计信息
- 处理文件冲突和错误情况
"""

import os
import re


def _get_pattern():
    """
    获取并返回用于匹配季集格式的正则表达式模式。

    Returns:
        tuple: (编译后的正则表达式对象, 原始模式字符串) 的元组。
    """
    pattern_string = r"[Ss](\d+)[-_\.]?[Ee](\d+)([-_\.]?[Ee]\d+)?"
    pattern = re.compile(pattern_string, re.IGNORECASE)
    return pattern, pattern_string


def _extract_base_key(match):
    """
    从正则匹配结果中提取标准化的基准键（SxxEyy 或 SxxEyy-Ezz）。

    Args:
        match (re.Match): 正则表达式匹配结果。

    Returns:
        str: 标准化的基准键，格式为 SxxEyy 或 SxxEyy-Ezz。
    """
    season_num = int(match.group(1))
    episode_num = int(match.group(2))
    double_episode_group = match.group(3)

    base_key = f"S{season_num:02d}E{episode_num:02d}"

    if double_episode_group:
        double_match = re.search(r"[Ee](\d+)", double_episode_group)
        if double_match:
            double_episode_num = int(double_match.group(1))
            base_key += f"-E{double_episode_num:02d}"

    return base_key


def _build_mkv_map(filenames, pattern):
    """
    构建 MKV 文件名到基准键的映射表。

    Args:
        filenames (list): 当前目录下的所有文件名列表。
        pattern (re.Pattern): 用于匹配季集格式的正则表达式。

    Returns:
        dict: 映射字典，key 为基准键（SxxEyy），value 为 MKV 文件名（不含扩展名）。
    """
    mkv_basename_map = {}
    mkv_files = [f for f in filenames if f.lower().endswith(".mkv")]

    for filename in mkv_files:
        name_only, _ = os.path.splitext(filename)
        match = pattern.search(name_only)

        if match:
            base_key = _extract_base_key(match)

            if base_key in mkv_basename_map:
                print(f"  [警告] 基准名 {base_key} 在 MKV 文件中重复 "
                      f"({mkv_basename_map[base_key]} 和 {name_only})。")

            mkv_basename_map[base_key] = name_only

    return mkv_basename_map


def _rename_single_ass_file(filename, dirpath, mkv_basename_map, pattern):
    """
    重命名单个 ASS 文件以匹配对应的 MKV 文件名。

    Args:
        filename (str): ASS 文件名。
        dirpath (str): 文件所在的目录路径。
        mkv_basename_map (dict): MKV 文件名映射表。
        pattern (re.Pattern): 用于匹配季集格式的正则表达式。

    Returns:
        tuple: (是否成功, 是否跳过) 的元组。成功返回 (True, False)，跳过返回 (False, True)，错误返回 (False, False)。
    """
    name_only, ext = os.path.splitext(filename)
    match = pattern.search(name_only)

    if not match:
        print(f"  [ASS跳过] 文件: {filename} - 文件名中未匹配到 SxxEyy 格式。")
        return False, True

    ass_base_key = _extract_base_key(match)

    if ass_base_key not in mkv_basename_map:
        print(f"  [ASS跳过] 文件: {filename} - 未找到同目录下匹配基准名 ({ass_base_key}) 的 MKV 文件。")
        return False, True

    target_mkv_name_base = mkv_basename_map[ass_base_key]
    new_filename = target_mkv_name_base + ext.lower()

    if filename == new_filename:
        print(f"  [ASS符合] 文件: {filename} - 已符合 MKV 原始文件名，跳过。")
        return False, True

    old_filepath = os.path.join(dirpath, filename)
    new_filepath = os.path.join(dirpath, new_filename)

    try:
        if os.path.exists(new_filepath) and new_filepath != old_filepath:
            print(f"  [警告] 目标 ASS 文件 {new_filename} 已存在，跳过重命名 {filename}。")
            return False, False

        os.rename(old_filepath, new_filepath)
        print(f"  [ASS成功] {filename} -> {new_filename} (匹配到 MKV 基准: {ass_base_key})")
        return True, False
    except OSError as e:
        print(f"  [ASS错误] 无法重命名 {filename}。错误信息: {e}")
        return False, False


def _process_directory(dirpath, dirnames, filenames, pattern):
    """
    处理单个目录中的文件重命名操作。

    Args:
        dirpath (str): 当前处理的目录路径。
        dirnames (list): 子目录名列表（可修改以排除某些目录，当前未使用但保留以兼容 os.walk）。
        filenames (list): 当前目录下的文件名列表。
        pattern (re.Pattern): 用于匹配季集格式的正则表达式。

    Returns:
        tuple: (成功重命名的文件数, 错误/警告数) 的元组。
    """
    # dirnames 参数保留以兼容 os.walk 的调用方式
    _ = dirnames
    print(f"\n当前目录: {dirpath}")
    print("  包含文件数:", len(filenames))

    mkv_basename_map = _build_mkv_map(filenames, pattern)
    print(f"  MKV基准名数量: {len(mkv_basename_map)}")

    ass_files = [f for f in filenames if f.lower().endswith(".ass")]
    total_ass_renamed = 0
    total_error = 0

    for filename in ass_files:
        success, skipped = _rename_single_ass_file(filename, dirpath, mkv_basename_map, pattern)
        if success:
            total_ass_renamed += 1
        elif not skipped:
            total_error += 1

    return total_ass_renamed, total_error


def rename_ass_to_match_mkv(root_dir):
    """
    遍历目录，将 ASS 文件重命名为与同目录下的 MKV 文件同名。
    MKV 文件名保持不变。

    Args:
        root_dir (str): 开始遍历的根目录。
    """
    pattern, pattern_string = _get_pattern()
    print("--- 调试信息：正则表达式 ---")
    print(f"使用的正则: {pattern_string}")
    print("----------------------------")

    print(f"开始遍历目录: {root_dir} (当前执行路径)")
    print("-" * 60)

    total_ass_renamed = 0
    total_error = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 排除对隐藏目录的遍历
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        renamed, errors = _process_directory(dirpath, dirnames, filenames, pattern)
        total_ass_renamed += renamed
        total_error += errors

    print("\n" + "=" * 60)
    print("所有文件重命名操作完成。")
    print(f"    - 总重命名 ASS 文件数: {total_ass_renamed}")
    print(f"    - 总错误/警告数: {total_error}")
    print("=" * 60)


def main():
    """
    主函数入口。
    
    默认在当前目录执行重命名操作，可以通过修改 root_directory 变量来指定其他目录。
    """
    root_directory = "."
    rename_ass_to_match_mkv(root_directory)


if __name__ == "__main__":
    main()
