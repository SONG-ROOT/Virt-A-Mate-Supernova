import os, json

def collect_file_list(unpack_dir, output_file="File_info.txt"):
    """收集文件列表"""
    
    # 读取已存在的包
    existing = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='gb18030', errors='ignore') as f:
            for line in f:
                if ':::' in line:
                    existing.add(line.split(':::')[0])
    
    # 获取需要处理的包
    packages = os.listdir(unpack_dir)
    # print(packages)
    packages_to_process = [p for p in packages if p not in existing]
    if not packages_to_process:
        print("没有新包需要处理")
        return
    
    print(f"处理 {len(packages_to_process)} 个新包...")
    
    with open(output_file, 'a', encoding='gb18030') as f:
        for i, package in enumerate(packages_to_process, 1):
            package_path = os.path.join(unpack_dir, package)
            items = set()
            
            # 收集文件和目录名（去扩展名）
            for root, dirs, files in os.walk(package_path):
                items.update(dirs)
                items.update(file.split(".")[0] for file in files)
            
            f.write(f"{package}:::{list(items)}\n")
            
            # 简单进度显示
            if i % 10 == 0:
                print(f"\r进度: {i}/{len(packages_to_process)}", end="")
    
    print(f"\n完成! 新增 {len(packages_to_process)} 个包")

if __name__ == "__main__":
    with open("config.json", 'r', encoding='utf-8') as f:
        DATA = json.load(f)
    
    UNPACK_DIR = DATA["paths"]["unzip_base_dir"]
    collect_file_list(UNPACK_DIR)
input("按任意键退出")