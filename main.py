from title_normalize import normalize
from config import *
from Levenshtein import distance
import pickle
import time


def find_nearest(title, title_dict):
    if title in title_dict:
        return title_dict[title]

    min_dist = EDIT_DISTANCE_THRESHOLD
    res = None
    for key in title_dict.keys():
        dist = distance(title, key)
        if dist < min_dist:
            min_dist = dist
            res = title_dict[key]
    return res


def run():
    with open(SRC_PATH, 'rb') as f:
        jobs = pickle.load(f)
        print('Job data loaded')
    with open(DICT_PATH, 'rb') as f:
        title_dict = pickle.load(f)
        print('Title data loaded')

    standard_title = []
    idx = 0
    for _, row in jobs.iterrows():
        idx += 1
        title = normalize(row['job_title'])
        standard_title.append(find_nearest(title, title_dict))
        if idx % 1000 == 0 or idx == len(jobs):
            print('\rProcessing %.3f%%...   ' % (100 * idx/len(jobs)), end='')
    print('Done!')

    jobs['standard_title'] = standard_title
    with open(DST_PATH, 'wb') as f:
        pickle.dump(jobs, f)


if __name__ == '__main__':
    start = time.time()
    run()
    print('All done! Time cost: ', time.time() - start)
