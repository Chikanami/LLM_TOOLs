import os
import re
from pathlib import Path

def merge_dated_files(output_filename="merged.txt", encoding="utf-8"):
    """
    将脚本同目录下 "输入" 文件夹中所有 YYYY-MM-DD.txt 文件按日期升序拼接，
    结果保存到同目录下 "输出" 文件夹。
    每个文件内容前会插入一个换行符、文件名、再换行，然后紧跟文件内容。
    """
    # 获取脚本所在目录
    script_dir = Path(__file__).resolve().parent
    input_dir = script_dir / "输入"
    output_dir = script_dir / "输出"
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查输入目录是否存在
    if not input_dir.exists():
        print(f"错误：输入文件夹不存在，请创建 '{input_dir}' 并放入文件。")
        return
    
    # 正则匹配 YYYY-MM-DD.txt
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.txt$")
    
    # 获取输入目录下所有匹配文件
    files = [f.name for f in input_dir.iterdir() if f.is_file() and pattern.match(f.name)]
    
    if not files:
        print(f"在 '{input_dir}' 中未找到格式为 YYYY-MM-DD.txt 的文件。")
        return
    
    # 按文件名（日期字符串）升序排序
    files.sort()
    print(f"找到 {len(files)} 个文件，将按以下顺序拼接：")
    for f in files:
        print(f"  {f}")
    
    # 打开输出文件进行写入
    output_path = output_dir / output_filename
    with open(output_path, "w", encoding=encoding) as out:
        for filename in files:
            # 每个文件名之前必须换行（第一个文件前也会有一个换行）
            out.write("\n")
            out.write(filename)
            out.write("\n")
            
            # 读取文件内容并原样写入
            file_path = input_dir / filename
            try:
                with open(file_path, "r", encoding=encoding) as inf:
                    out.write(inf.read())
            except UnicodeDecodeError:
                print(f"警告：文件 {filename} 编码可能不是 {encoding}，尝试使用系统默认编码。")
                with open(file_path, "r", encoding="gbk", errors="replace") as inf:
                    out.write(inf.read())
    
    print(f"\n拼接完成，结果已保存至：{output_path}")

if __name__ == "__main__":
    # 可修改输出文件名或编码
    merge_dated_files("merged.txt", "utf-8")