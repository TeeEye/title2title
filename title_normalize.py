import re
from collections import Counter

import Levenshtein
import jieba
import pandas as pd
from config import *

TITLE_NORMALIZE_INITIATED = False

stopwords = None
citys = None


# 统一为英文标点&英文小写 & 去除无用标点及特殊字符
def normalize_punc_case(title):
    # 中英&全半角替换
    intab = "。？！，；：“”‘’（）《》￥【】『』「」｛｝、—－～➕＋．／［＼］｜‖–＃＊⼊⼯⽅⽤⽬⾏|\\·\t丶"
    outtab = ".?!,;:\"\"\'\'()<>$[]{}{}{}/--~++./[/]//-#*入工方用目行//. /"
    for x in range(65281, 65374 + 1):
        if chr(x) not in intab:
            intab += chr(x)
            outtab += chr(x - 65248)
    trans_table = str.maketrans(intab, outtab)
    title = title.translate(trans_table)
    title = title.lower()
    # 去掉特殊字符
    title = re.sub(
        "[`丨!,*:;=?^~\"\'️㊣★￼㎡•⚽🏀\xa0\x7f\x08\u200b\u3000\ue98b\uf06c\uf0b7" +
        "\U001002c4\U001002c5\U001004ea\U0010166b\U00102d01\U00102d1e\U0010434f\U00104353\U00104ea9\n]",
        "", title)
    return title.strip()


def isletter(s):
    if 'a' <= s <= 'z':
        return True
    if 'A' <= s <= 'Z':
        return True
    return False


# 处理空格
def normalize_space(title):
    if title.find(" ") < 0:
        return title
    # title = re.sub("\s{2,}", " ", title)
    new_title = []
    last_english = False
    idx = 0
    while idx < len(title):
        s = title[idx]
        next_english = False
        if idx + 1 < len(title):
            next_english = isletter(title[idx + 1])
        if s == " " and last_english and next_english:
            new_title.append(s)
            last_english = False
            idx += 1
            continue
        if s != " ":
            new_title.append(s)
        last_english = isletter(s)
        idx += 1
    return "".join(new_title)


# 去除括号内容 () [] {} <> 以及括号本身
def clear_brackets(title):
    title = re.sub('\\(.*?\\)|\\[.*?\\]|{.*?}|<.*?>', "", title).strip()
    # 处理单个括号
    title = re.sub('[\(\)\[\]\{\}<>]', "", title).strip()
    return title


# 去除字母数组下划线组合式ID信息
def clear_id(title):
    return re.sub("[a-zA-Z]*\d*-*[a-zA-Z]*\d{2,}[a-zA-Z]*\d*-*", "", title).strip()


# 去除字典内信息
def clear_stopwords(title):
    for word in stopwords:
        if word in title:
            title = title.replace(word, "")
    return title.strip()

# 将多个+-/连字符合并为一个
def merge_hyphen(title):
    title = str(title)
    if title.find("c++") < 0:
        title = re.sub("\+{2,}", "+", title)
    if title.find("cocos2d") < 0:
        title = re.sub("-", "", title)
    title = re.sub("/{2,}", "/", title)
    return title


# 去除首尾标点字符
def my_strip(title):
    if title.find(".net") > -1:
        if title.find("c++") > -1:
            return title.strip("*?&%~#=/\-,:()> ")
        else:
            return title.strip("+*?&%~#=/\-,:()> ")
    else:
        if title.find("c++") > -1:
            return title.strip(".*?&%~#=/\-,:()> ")
        else:
            return title.strip(".+*?&%~#=/\-,:()> ")


def special_rules(title):
    new_title = title
    # 处理城市
    words = jieba.lcut(title)
    if len(words) > 0:
        new_title = ""
        for word in words:
            if word in cities:
                continue
            new_title += word
    # 处理"诚招"
    if "诚招" in words:
        new_title = "".join(words[words.index("诚招") + 1:])
    # 处理"届" "聘" "岗" "某"
    new_title = new_title.strip("届")
    new_title = new_title.lstrip("聘")
    new_title = new_title.rstrip("岗")
    new_title = new_title.lstrip("某")
    new_title = new_title.lstrip("招")
    return new_title


# 处理中英文同义数据
def translate(title, youdao, regexs):
    source_title = title
    title = regexs.get("separator").sub("", title)
    index_en = regexs.get("en").search(title).regs[0][0]
    index_zh = regexs.get("zh").search(title).regs[0][0]
    title_en, title_zh = "", ""
    if index_en == 0:
        title_en = title[0:index_zh]
        title_zh = title[index_zh:]
    if index_zh == 0:
        title_zh = title[0:index_en]
        title_en = title[index_en:]
    if title_zh.strip() in youdao.en_to_zh(title_en, multi=False):
        return title_zh, title_en
    if title_en.strip() in youdao.zh_to_en(title_zh, multi=False):
        return title_zh, title_en
    return source_title, ""


# 去除重复和歧义数据
def disambiguation(df_titles):
    duplicated_data = df_titles[df_titles.duplicated(['title'], keep=False)]
    no_duplicated_data = df_titles[~df_titles.duplicated(['title'], keep=False)]
    print(duplicated_data.shape)
    print(no_duplicated_data.shape)
    new_data = pd.DataFrame(columns=df_titles.columns)
    gb_duplicated = duplicated_data.groupby(by="title")
    for title, data in gb_duplicated:
        # 1.title与三级分类相同
        third_categories_lower = [i.lower() for i in data['third_category']]
        if title.strip() in third_categories_lower:
            data['lower'] = data['third_category'].apply(str.lower)
            temp_data = data[data['lower'] == title.strip()].drop_duplicates('title')
            temp_data.pop('lower')
            new_data = new_data.append(temp_data, ignore_index=True)
        else:
            # 2.选举模式
            counter = Counter(list(data['third_category']))
            temp_third, count = counter.most_common(1)[0]
            if count > 1:
                new_data = new_data.append(data[data['third_category'] == temp_third].drop_duplicates('title'),
                                           ignore_index=True)
            else:
                # 3.编辑距离最小
                data['distance'] = data.apply(
                    lambda row: Levenshtein.distance(row['title'], row['third_category'].lower()), axis=1)
                data.sort_values(by="distance", inplace=True, ascending=True)
                data.pop('distance')
                new_data = new_data.append(data.iloc[0])
    print(new_data.shape)
    no_duplicated_data = no_duplicated_data.append(new_data, ignore_index=True)
    return no_duplicated_data


re_vaild = re.compile("[\u4e00-\u9fa5a-zA-Z0-9]")


def normalize(title):
    if not TITLE_NORMALIZE_INITIATED:
        init()
    if not re_vaild.search(title):
        return None
    title = normalize_punc_case(title)
    title = normalize_space(title)
    title = clear_brackets(title)
    title = clear_id(title)
    title = clear_stopwords(title)
    title = special_rules(title)
    title = merge_hyphen(title)
    title = my_strip(title)
    return title if len(title) > 1 else None


def init():
    global TITLE_NORMALIZE_INITIATED
    if TITLE_NORMALIZE_INITIATED:
        return
    TITLE_NORMALIZE_INITIATED = True
    global stopwords
    stopwords = [line.strip() for line in open(STOP_WORD_PATH, "r", encoding="utf-8")]
    global cities
    cities = [line.strip() for line in open(CITY_PATH, "r", encoding="utf-8")]
    jieba.load_userdict(CITY_PATH)
