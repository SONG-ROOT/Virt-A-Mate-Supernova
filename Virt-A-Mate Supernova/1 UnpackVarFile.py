import os
import zipfile
from tqdm import tqdm
import json
import shutil

with open("config.json", 'r', encoding='utf-8') as f:
    DATA = json.load(f)

input_dir = DATA["paths"]["var_scan_dir"]
output_dir = DATA["paths"]["unzip_base_dir"]
error_dir = os.path.join(os.path.dirname(input_dir), "压缩包损坏")  # 损坏文件存放目录

# 获取所有var文件
var_files = [f for f in os.listdir(input_dir) if f.endswith('.var')]
if not var_files:
    print("未找到var文件")
    exit()

# 创建输出目录
os.makedirs(output_dir, exist_ok=True)
count = 0
error_dir_ = []

for var_file in tqdm(var_files, desc="解压进度"):
    name = var_file[:-4]  # 去掉.var后缀
    output_path = os.path.join(output_dir, name)
    
    # 如果目录已存在则跳过
    if os.path.exists(output_path):
        count+=1
        continue
    
    try:
        path_ = os.path.join(input_dir, var_file)
        # print(path_)
        with zipfile.ZipFile(path_, 'r') as zf:
            zf.extractall(output_path)
    except:
        error_dir_.append(path_)
        print(path_,'解压错误')
        # raise

print(f"解压完成，共处理{len(var_files)}个文件")
print(error_dir_)
print(len(error_dir_))

for file_path in error_dir_:
    target_path = file_path.replace(input_dir, "已损坏的包")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.move(file_path, target_path)
input("按任意键退出")
