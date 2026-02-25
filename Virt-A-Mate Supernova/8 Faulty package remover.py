import os
import zipfile
import json
from tqdm import tqdm  # 导入进度条库
import csv
import shutil

# 1 首先删除output_dir中的空文件夹
def delate_empty_folder():
    with open("config.json", 'r', encoding='utf-8') as f:
        DATA = json.load(f)

    input_dir = DATA["paths"]["var_scan_dir"]
    output_dir = DATA["paths"]["unzip_base_dir"]
    files = os.listdir(output_dir)

    empty_list = []

    # 使用 tqdm 包装迭代器，显示进度条
    for i in tqdm(files, desc="检查空文件夹", unit="个"):
        folder_path = os.path.join(output_dir, i)
        if not os.listdir(folder_path):
            empty_list.append(i)
            print(f"\n发现空文件夹: {folder_path}")

    print(f"\n检查完成！共发现 {len(empty_list)} 个空文件夹：")
    print(empty_list)

    # 第三步：删除空文件夹（可选）
    for i in empty_list:
        folder_path = os.path.join(output_dir, i)
        try:
            os.rmdir(folder_path)
            print(f"已删除空文件夹: {folder_path}")
        except Exception as e:
            print(f"删除文件夹失败 {folder_path}: {e}")


# 2 删除var_packages中的对应项
def delete_rows():
    input_file = "var_packages.csv"
    output_file = "var_packages.csv"
    
    # 读取并筛选
    rows_to_keep = []
    c = 0
    with open(input_file, 'r', encoding='gb18030') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # 只保留 images_copied > 0 且 dependencies != "无meta.json" 的行
            try:
                images_copied = int(row.get('images_copied', '0'))
            except ValueError:
                images_copied = 0
            
            dependencies = row.get('dependencies', '')
            
            # if (images_copied > 0) and (dependencies != "无meta.json") and dependencies != "meta.json解析错误":
            if dependencies != "meta.json解析错误":
                rows_to_keep.append(row)
            else:
                c+=1
                print(f"删除: {row.get('filename', '未知')}")
    print(c)
    # 写入新文件
    with open(output_file, 'w', newline='', encoding='gb18030') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_to_keep)
    
    print(f"\n完成！保留 {len(rows_to_keep)} 条记录")
    print(f"新文件: {output_file}")


# =================== 第三步：删除output_dir中对应的文件夹 ===================
def delete_output_dir():
    # 1 首先删除output_dir中的空文件夹
    with open("config.json", 'r', encoding='utf-8') as f:
        DATA = json.load(f)

    input_dir = DATA["paths"]["var_scan_dir"]
    output_dir = DATA["paths"]["unzip_base_dir"]
    files = os.listdir(output_dir)

    # 3 删除output_dir中的对应文件夹
    
    print("\n" + "=" * 60)
    print("第三步：删除output_dir中对应的文件夹")
    print("=" * 60)

    # 读取筛选后的CSV文件，获取需要保留的文件夹列表
    kept_folders = []

    with open("var_packages.csv", 'r', encoding='gb18030') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get('filename', '')
            if filename:
                # 去掉.zip扩展名，获取文件夹名
                folder_name = filename.replace('.zip', '')
                kept_folders.append(folder_name)
    kept_folders = [f.replace('.var', '') for f in kept_folders]

    print(f"CSV中保留的文件夹数量: {len(kept_folders)}")
    # 获取output_dir中所有的文件夹
    all_folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]

    print(f"output_dir中的文件夹数量: {len(all_folders)}")

    # 找出需要删除的文件夹（在output_dir中存在但不在CSV保留列表中的）
    folders_to_delete = [f for f in all_folders if f not in kept_folders]

    print(f"需要删除的文件夹数量: {len(folders_to_delete)}")

    # 删除这些文件夹
    c = 0
    if folders_to_delete:
        print("\n开始删除文件夹...")
        for folder_name in tqdm(folders_to_delete, desc="删除文件夹", unit="个"):
            folder_path = os.path.join(output_dir, folder_name)
            try:
                c+=1
                # 使用shutil.rmtree删除整个文件夹（包括子文件夹和文件）
                shutil.rmtree(folder_path)
                print(f"已删除: {folder_path}")
            except Exception as e:
                print(f"删除失败 {folder_path}: {e}")
    else:
        print("\n没有需要删除的文件夹")

    print("\n" + "=" * 60)
    print("清理完成！")
    print(f"原始文件夹数: {len(all_folders)}")
    print(f"保留文件夹数: {len(kept_folders)}")
    print(f"删除文件夹数: {len(folders_to_delete)}")
    print("=" * 60)
    print(c)

# =================== 第四步：对比var_packages和var_analysis_results，删除多余记录 ===================
def delete_var_analysis_results():
    print("\n" + "=" * 60)
    print("第四步：对比CSV文件，删除var_analysis_results中的多余记录")
    print("=" * 60)

    var_packages_file = "var_packages.csv"
    var_analysis_file = "var_analysis_results.csv"
    output_file = "var_analysis_results.csv"

    try:
        # 读取var_packages.csv中保留的文件名（去掉扩展名）
        kept_filenames = set()
        
        print("读取var_packages.csv中的保留文件名...")
        with open(var_packages_file, 'r', encoding='gb18030') as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get('filename', '')
                if filename:
                    # 统一处理.var和.zip扩展名
                    base_name = filename.replace('.var', '').replace('.zip', '')
                    kept_filenames.add(base_name)
        
        print(f"var_packages.csv中保留的文件数量: {len(kept_filenames)}")
        
        # 读取var_analysis_results.csv并对比
        rows_to_keep = []
        deleted_count = 0
        kept_count = 0
        
        print("对比var_analysis_results.csv...")
        with open(var_analysis_file, 'r', encoding='gb18030') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row in tqdm(reader, desc="处理记录", unit="行"):
                filename = row.get('filename', '')
                
                if filename:
                    # 检查文件名是否以.var结尾
                    if filename.endswith('.var'):
                        base_name = filename.replace('.var', '')
                        # 如果这个文件不在var_packages.csv的保留列表中，则删除
                        if base_name in kept_filenames:
                            rows_to_keep.append(row)
                            kept_count += 1
                        else:
                            print(f"删除多余记录: {filename}")
                            deleted_count += 1

        print(len(rows_to_keep),"11")
        # 写入新文件
        with open(output_file, 'w', newline='', encoding='gb18030') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_to_keep)
        
        print(f"\n对比完成!")
        print(f"var_packages.csv保留文件数: {len(kept_filenames)}")
        print(f"var_analysis_results.csv原始记录数: {kept_count + deleted_count}")
        print(f"删除的多余记录数: {deleted_count}")
        print(f"保留的记录数: {kept_count}")
        print(f"新文件已保存为: {output_file}")
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 {e.filename}")
    except Exception as e:
        print(f"处理文件时发生错误: {e}")

    print("=" * 60)



# 通过对比var_packages.csv生成要删除的文件名列表
def get_files_to_delete_from_csv():
    """从File_info.txt和var_packages.csv对比，找出需要删除的文件"""
    file_info_path = "File_info.txt"
    var_packages_path = "var_packages.csv"
    
    try:
        # 读取var_packages.csv中的所有文件名（去掉扩展名）
        print("读取var_packages.csv中的文件名...")
        with open(var_packages_path, 'r', encoding='gb18030') as f:
            reader = csv.DictReader(f)
            var_packages_files = set()
            
            for row in reader:
                filename = row.get('filename', '')
                if filename:
                    # 去掉扩展名
                    base_name = filename.replace('.var', '').replace('.zip', '')
                    var_packages_files.add(base_name)
        
        print(f"var_packages.csv中记录的文件数: {len(var_packages_files)}")
        
        # 读取File_info.txt中的所有文件名
        print("读取File_info.txt中的文件名...")
        with open(file_info_path, 'r', encoding='gb18030') as f:
            lines = f.readlines()
        
        file_info_files = set()
        for line in lines:
            line = line.strip()
            if line and ':::' in line:
                filename = line.split(':::')[0].strip()
                if filename:
                    file_info_files.add(filename)
        
        print(f"File_info.txt中记录的文件数: {len(file_info_files)}")
        
        # 找出在File_info.txt中存在，但不在var_packages.csv中的文件
        files_to_delete = file_info_files - var_packages_files
        
        print(f"\n需要删除的文件数量: {len(files_to_delete)}")
        print("需要删除的文件名:")
        for i, filename in enumerate(sorted(files_to_delete), 1):
            print(f"  {i}. {filename}")
        
        return list(files_to_delete)
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 {e.filename}")
        return []
    except Exception as e:
        print(f"处理文件时发生错误: {e}")
        return []

# 然后使用这个函数清理File_info.txt
def clean_file_info_with_csv():
    """使用var_packages.csv对比清理File_info.txt"""
    input_file = "File_info.txt"
    output_file = "File_info_1.txt"
    
    # 获取要删除的文件列表
    files_to_delete = get_files_to_delete_from_csv()
    
    if not files_to_delete:
        print("没有需要删除的文件")
        return
    
    kept_count = 0
    deleted_count = 0
    
    try:
        with open(input_file, 'r', encoding='gb18030') as infile, \
             open(output_file, 'w', encoding='gb18030') as outfile:
            
            for line in infile:
                line = line.strip()
                if not line:
                    continue
                    
                # 提取文件名
                if ':::' in line:
                    filename = line.split(':::')[0].strip()
                else:
                    filename = line.strip()
                
                # 检查是否需要删除
                if filename in files_to_delete:
                    deleted_count += 1
                    if deleted_count <= 5:  # 只打印前5个删除的文件
                        print(f"删除: {filename}")
                else:
                    outfile.write(line + '\n')
                    kept_count += 1
        
        print(f"\n清理完成!")
        print(f"原始文件: {input_file}")
        print(f"新文件: {output_file}")
        print(f"删除行数: {deleted_count}")
        print(f"保留行数: {kept_count}")
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
    except Exception as e:
        print(f"处理文件时发生错误: {e}")

def delete_others():
    import os
    for file in ["dependency_stats.csv", "authors_categories.csv"]:
        os.remove(file) if os.path.exists(file) else print(f"{file} 不存在")
    print("删除完成")



# delate_empty_folder()
# delete_rows()
# delete_output_dir()
# delete_var_analysis_results()
# clean_file_info_with_csv()
# delete_others()
