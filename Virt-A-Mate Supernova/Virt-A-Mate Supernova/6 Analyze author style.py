import csv
from collections import defaultdict

VALID_TAGS = {'外观预设', '皮肤预设', '插件预设', '头发预设', '声音', '外观json', 
              '纹理', 'General', '场景', '姿势', 'SubScene', '衣服预设', 
              '插件', '资产', '变形', '衣服', '头发'}

# 标签到分类的映射
TAG_TO_CATEGORY = {
    '衣服预设': '服装预设专精设计师',
    '衣服': '服装专精设计师',
    '头发预设': '头发预设专精设计师',
    '头发': '头发专精设计师',
    '场景': '场景专精设计师',
    'SubScene': 'SubScene专精设计师',
    '姿势': '姿势专精设计师',
    '外观预设': '外观专精设计师',
    '皮肤预设': '皮肤预设专精设计师',
    '外观json': '外观专精设计师',
    '插件预设': '插件专精设计师',
    '插件': '插件专精设计师',
    '声音': '声音专精设计师',
    '纹理': '纹理专精设计师',
    'General': '通用专精设计师',
    '资产': '资产专精设计师',
    '变形': '变形专精设计师'
}


def get_dominant_categories(tag_ratios, threshold=55):
    """获取主导类别（比例超过threshold的类别）"""
    dominant = []
    for tag, ratio in tag_ratios.items():
        if ratio >= threshold:
            dominant.append(tag)
    return dominant
def analyze_dominant_combination(dominant_categories):
    """分析主导类别的组合"""
    dominant_set = set(dominant_categories)
    
    # 作者风格分类
    if len(dominant_set) == 0:
        return "没有明显的倾向"
    if {"衣服"} == (dominant_set):
        return "服装专精设计师"
    if {"资产"} == (dominant_set):
        return "资产专精设计师"
    if {'衣服预设', '衣服'}== (dominant_set):
        return "服装专精设计师"
    if {'头发'} == (dominant_set):
        return "头发专精设计师"
    if {'头发预设', '头发'} == (dominant_set):
        return "头发专精设计师"
    if {'插件'} == (dominant_set):
        return "插件专精设计师"
    if {'姿势'} == (dominant_set) or {'姿势', '变形'} == (dominant_set) :
        return "姿势专精设计师"
    if {'纹理'} == (dominant_set):
        return "纹理专精设计师"

    if {'场景', '资产'} == (dominant_set):
        return "空环境设计师"
    if {'场景', '衣服'} == (dominant_set):
        return "服装专精设计师"
    if {'插件', '变形'} == (dominant_set):
        return "插件设计师"

    if {'场景', '衣服', '资产'} == (dominant_set):
        return "服装主导者设计师"

    if {'场景', "变形"} == (dominant_set):
        return "变形 人物卡设计师"
    if {'场景'}.issubset (dominant_set) and len(dominant_set)>=3:
        return "人物卡设计师"

    # if {'场景', '纹理',"变形"} == (dominant_set):
    #     return "纹理+变形 人物卡设计师"
    # if {'场景', "变形", "衣服","纹理"} == (dominant_set):
    #     return "纹理+变形+衣服 人物卡设计师"
    # if {'场景', "变形", "衣服","纹理","插件","SubScene"} == (dominant_set):
    #     return "纹理+变形+衣服+插件+SubScene 人物卡设计师"
    # if {"变形","纹理","场景", "资产"} == (dominant_set):
    #     return "纹理+变形+资产 人物卡设计师"  
    # if {'纹理', '变形', 'SubScene', '资产', '场景'} == (dominant_set):
    #     return "纹理+变形+资产+SubScene 人物卡设计师"
    # if {'场景', '变形', '纹理', '头发'} == (dominant_set):
    #     return "场景+头发+变形+纹理 人物卡设计师"
    # if {'场景', '衣服', '变形', '头发', '纹理'} == (dominant_set):
    #     return "场景+头发+衣服+变形+纹理 人物卡设计师"
    # if {'场景', '资产', '衣服', '变形', '纹理'} == (dominant_set):
    #     return "场景+资产+衣服+变形+纹理 人物卡设计师"
    # if {'外观预设', '变形', 'SubScene', '纹理', '场景'} == (dominant_set):
    #     return "外观预设+SubScene+变形+纹理 人物卡设计师"
    # if {'SubScene', '纹理', '变形', '场景'} == (dominant_set):
    #     return "场景和人物卡设计师"
    # if {'场景', '纹理', '头发'}== (dominant_set):
    #     return "纹理+头发 人物卡设计师"

    if {'场景'} == (dominant_set) or {'场景', 'SubScene'}== (dominant_set):
        return "场景专精设计师"
    
    # if {'变形', '场景', '插件', '资产'}.issubset(dominant_set):
    #     return "AAA"

    return None



def load_data():
    """加载CSV数据并统计作者标签信息"""
    authors = defaultdict(lambda: defaultdict(int))
    
    try:
        with open('var_packages.csv', 'r', encoding='gb18030') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("⚠️ CSV文件为空或格式不正确")
                return authors
                
            for row in reader:
                author = row.get('author', '').strip()
                if not author:
                    continue
                
                tags = {tag.strip() for tag in row.get('tags', '').split(',') if tag.strip()}
                valid_tags = tags & VALID_TAGS
                
                authors[author]['total_packages'] += 1
                for tag in valid_tags:
                    authors[author][tag] = authors[author].get(tag, 0) + 1
                    
    except FileNotFoundError:
        print("❌ 未找到文件 'var_packages.csv'")
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")
    
    return authors

def analyze_author_tags(author_stats):
    """分析作者标签分布，返回标签比例"""
    total = author_stats['total_packages']
    tag_ratios = {}
    
    for tag in VALID_TAGS:
        count = author_stats.get(tag, 0)
        tag_ratios[tag] = count / total * 100 if total > 0 else 0
    
    return tag_ratios

def get_persona_card_type(tag_ratios):
    """判断人物卡类型，返回类型名称或None"""
    scene_ratio = tag_ratios.get('场景', 0)
    transform_ratio = tag_ratios.get('变形', 0)
    subscene_ratio = tag_ratios.get('SubScene', 0)
    texture_ratio = tag_ratios.get('纹理', 0)
    
    # 计算场景相关标签的总比例
    scene_total_ratio = scene_ratio + subscene_ratio
    
    # 类型1：场景+纹理+变形人物卡设计师
    # 要求：这三种标签各自都很高，且总占比极高
    if (scene_total_ratio >= 85 and 
        transform_ratio >= 85 and 
        texture_ratio >= 85):
        
        # 检查其他标签是否很少
        other_tags_ratio = sum(
            ratio for tag, ratio in tag_ratios.items() 
            if tag not in ['场景', '变形', '纹理', 'SubScene']
        )
        
        if other_tags_ratio <= 15:
            return "纹理变形人物卡设计师"
    
    # 类型2：场景+变形人物卡设计师
    # 要求：场景和变形都很高，且总占比较高
    elif (scene_total_ratio >= 75 and 
          transform_ratio >= 75):
        
        # 检查其他标签是否很少
        other_tags_ratio = sum(
            ratio for tag, ratio in tag_ratios.items() 
            if tag not in ['场景', '变形', 'SubScene']
        )
        
        # 纹理可以是次要标签
        texture_ratio = tag_ratios.get('纹理', 0)
        if other_tags_ratio <= 25 or (other_tags_ratio - texture_ratio <= 20):
            return "变形人物卡设计师"
    
    return None

def determine_category(tag_ratios, threshold=55):
    """根据标签比例确定作者分类"""
    
    # # 首先检查是否为人物卡设计师
    # persona_type = get_persona_card_type(tag_ratios)
    # if persona_type:
    #     return persona_type
    

    # 获取主导类别（新增的关键代码）
    dominant_categories = get_dominant_categories(tag_ratios)


    # 按比例降序排序标签
    sorted_tags = sorted(tag_ratios.items(), key=lambda x: x[1], reverse=True)
    
    if not sorted_tags:
        return "其他"

    if any(tag_name == "声音" for tag_name, score in sorted_tags) and "声音" in dominant_categories:
        return "含声音XXOO场景专业设计大师"
    # 获取最高比例的标签
    main_tag, main_ratio = sorted_tags[0]
    
    # # 如果主要标签比例超过阈值
    # if main_ratio >= threshold:
    #     # 检查是否为主要标签（有对应的分类）
    #     if main_tag in TAG_TO_CATEGORY:
    #         # 检查第二高的标签是否显著（超过 threshold/3）
    #         if len(sorted_tags) > 1:
    #             second_ratio = sorted_tags[1][1]
    #             # if second_ratio > (threshold / 3):
    #             #     return "综合设计师"
    #         return TAG_TO_CATEGORY[main_tag]
    # 检查 sorted_tags 中是否有第一个元素为 "声音" 的元组



    # 分析主导类别组合（新增的关键代码）
    dominant_combination = analyze_dominant_combination(dominant_categories)
    if dominant_combination:
        return dominant_combination
    else:
        return dominant_categories
    # # 检查是否有多个显著标签
    # significant_tags = [(tag, ratio) for tag, ratio in sorted_tags if ratio >= 30]
    # if len(significant_tags) >= 2:
    #     # 如果显著标签中包含场景和变形，但比例不够高，则可能是普通人物卡设计师
    #     if ('场景' in [t[0] for t in significant_tags] or 
    #         'SubScene' in [t[0] for t in significant_tags]) and \
    #        '变形' in [t[0] for t in significant_tags]:
    #         scene_related = sum(ratio for tag, ratio in significant_tags 
    #                           if tag in ['场景', 'SubScene'])
    #         transform_ratio = next((ratio for tag, ratio in significant_tags 
    #                               if tag == '变形'), 0)
        
    #     return "综合设计师"

def get_author_categories(authors, min_packages=3): # 2个及以下下包的作者不统计
    """获取作者分类"""
    categories = {}
    
    for author, stats in authors.items():
        total = stats['total_packages']
        
        # 跳过作品太少的作者
        if total < min_packages:
            continue
        
        # 分析标签分布
        tag_ratios = analyze_author_tags(stats)

        # if author == "enoeht":
        #     print("作者: ",author)
        #     print(tag_ratios) 
        #     print(set(category))

        if 20 < float( tag_ratios["声音"]) <55:
            categories[author] = {
                'category': "含声音XXOO场景设计大师",
                'total_packages': total,
                'tag_ratios': tag_ratios
            }
            continue

        # Debug
        category = determine_category(tag_ratios, threshold=55)

        if author == "Archer":
            print("作者: ",author)
            print(tag_ratios) 
            print(set(category))
        
        if str(type(category)) != "<class 'list'>":
            # print(type(category) )
            # 只记录有明确分类的作者
            categories[author] = {
                'category': category,
                'total_packages': total,
                'tag_ratios': tag_ratios
            }
    return categories

def save_results(categories, filename='authors_categories.csv'):
    """保存结果到CSV文件"""
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['author', 'category', '作品数量', '主要标签分布(%)'])
        
        for author, data in sorted(categories.items()):
            # 格式化标签分布（只显示比例>5%的标签）
            significant_tags = [
                f'{tag}:{ratio:.1f}%' 
                for tag, ratio in sorted(data['tag_ratios'].items(), key=lambda x: x[1], reverse=True)
                if ratio > 5
            ]
            tag_ratios_str = '; '.join(significant_tags) if significant_tags else '无显著标签'
            
            writer.writerow([
                author, 
                data['category'], 
                data['total_packages'],
                tag_ratios_str
            ])
    
    print(f"✅ 已保存 {len(categories)} 位作者到 '{filename}'")
    
    # 输出分类统计
    print("\n📊 分类统计:")
    category_counts = defaultdict(int)
    for data in categories.values():
        category_counts[data['category']] += 1
    
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}人")
    
    # 特别统计人物卡设计师
    print("\n🎭 人物卡设计师细分:")
    persona_categories = [c for c in category_counts.keys() if '人物卡' in c]
    for category in persona_categories:
        print(f"  {category}: {category_counts[category]}人")

if __name__ == "__main__":
    authors = load_data()
    print(f"📈 共加载 {len(authors)} 位作者的数据")
    
    categories = get_author_categories(authors)
    save_results(categories)
input("按任意键退出")