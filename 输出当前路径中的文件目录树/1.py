import os
import datetime
from datetime import datetime

def format_size(size_bytes):
    """将字节大小转换为易读的格式 (KB, MB, GB)"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0 or unit == 'GB':
            break
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{int(size_bytes)} {unit}"

def list_directory_structure(output_file):
    """
    列出当前目录及其子目录中的所有文件夹和文件（含体积信息），并保存到文本文件
    :param output_file: 输出文件名
    """
    total_files = 0
    total_dirs = 0
    total_size = 0
    largest_file = ("", 0)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入标题
        f.write(f"目录结构列表 (生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"生成脚本: {os.path.abspath(__file__)}\n\n")
        
        # 获取当前工作目录
        root_dir = os.getcwd()
        f.write(f"根目录: {root_dir}\n\n")
        
        # 遍历所有目录和文件
        for root, dirs, files in os.walk(root_dir):
            # 排除脚本自身和输出文件
            dirs[:] = [d for d in dirs if d != '__pycache__']  # 排除编译文件夹
            files = [file for file in files if file != os.path.basename(__file__) 
                     and file != output_file]
            
            # 计算缩进级别
            level = root.replace(root_dir, '').count(os.sep)
            indent = '│   ' * (level - 1) + '├── ' if level > 0 else ''
            
            # 写入当前目录
            dir_name = os.path.basename(root) or root_dir
            f.write(f'{indent}{dir_name}/\n')
            total_dirs += 1
            
            # 写入子目录
            subindent = '│   ' * level + '├── '
            for d in sorted(dirs):
                f.write(f'{subindent}{d}/\n')
                total_dirs += 1
            
            # 写入文件（带体积信息）
            file_indent = '│   ' * level + '├── '
            for file in sorted(files):
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    total_files += 1
                    
                    # 记录最大文件
                    if file_size > largest_file[1]:
                        largest_file = (os.path.join(root, file), file_size)
                    
                    size_str = format_size(file_size)
                    f.write(f'{file_indent}{file} ({size_str})\n')
                except OSError as e:
                    f.write(f'{file_indent}{file} [访问错误: {str(e)}]\n')
        
        # 添加统计信息
        f.write("\n" + "=" * 50 + "\n")
        f.write("目录统计摘要:\n")
        f.write(f"- 目录总数: {total_dirs} 个\n")
        f.write(f"- 文件总数: {total_files} 个\n")
        f.write(f"- 总文件体积: {format_size(total_size)}\n")
              
        # 添加目录信息
        f.write(f"\n扫描范围: {root_dir}\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    output_filename = "directory_structure.txt"
    
    print("正在扫描目录结构并计算文件体积...")
    start_time = datetime.now()
    list_directory_structure(output_filename)
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"完成! 扫描耗时: {duration:.2f} 秒")
    print(f"结果已保存到: {os.path.abspath(output_filename)}")