import re
import sys
import pandas as pd
from collections import Counter
from camel_tools.utils.charmap import CharMapper
from camel_tools.morphology.database import MorphologyDB

bw2ar = CharMapper.builtin_mapper('bw2ar')
ar2bw = CharMapper.builtin_mapper('ar2bw')

_REMOVE_CLTCS = re.compile(r'(\S+\+\_|\_\+\S+)')
_REMOVE_FNL_DCRTC = re.compile(r'([iouaFKN]|AF)$')
_NORM_SOUND = re.compile(r'uwn$')
_PRC_STR = re.compile(r'(\S+\+\_)+')
_ECN_STR = re.compile(r'(\_\+\S+)+')
_UNDRSCR_PLS = re.compile(r'[\+\_]')
_SUKUN = re.compile(r'o')

def _trim_corpus(file_path, threshold):
    words = []
    lemmas = []
    with open(file_path, 'r') as f:
        for line in f:
            if not line.startswith('*'):
                continue

            features = _parse_analysis_line_toks(line.strip().split(' ')[1:])
            lemmas.append(features['lex'])
            words.append(features['diac'])
    word_counts = Counter(words)
    word_counts = Counter({k: c for k, c in word_counts.items() if c > threshold})
    lemma_counts = Counter(lemmas)
    lemma_counts = Counter({k: c for k, c in lemma_counts.items() if c > threshold})

    return word_counts, lemma_counts



def _parse_analysis_line_toks(toks):
    res = {}

    for tok in toks:
        if len(tok) == 0:
            continue

        subtoks = tok.split(u':')
        if len(subtoks) < 2:
            print('invalid key value pair {}'.format(repr(tok)))

        res[subtoks[0]] = u':'.join(subtoks[1:])

    return res

def _generate_cv_template(patt, pl_type, pl_sg='s'):

    # remove sukun
    template = _SUKUN.sub('', patt)

    # handle sound plurals
    if pl_type == 'S' and pl_sg == 'p':
        if patt.endswith('At'):
            template = re.sub('At$', '+aat', template)
        elif patt.endswith('|t'):
            template = re.sub('At$', '2+aat', template)
        elif patt.endswith(('iyn', 'uwn')):
            template = re.sub('iyn$', '+iin', template)
            template = re.sub('uwn$', '+uun', template)
        elif patt.endswith(('iy', 'uw')):
            template = re.sub('iy$', '+ii', template)
            template = re.sub('uw$', '+uu', template)
        else:
            print("What kind sound plular is this يا روح أمك?")
            print(patt)


    # consonants
    template = re.sub(r'\d', 'C', template)

    # treat long vowel aa and glotal stop ending as a suffix
    template = re.sub(r"A'$", '+aa2', template)

    # treat aan as a suffix
    template = re.sub(r"An$", "+aan", template)

    # long vowels aa, ii, uu
    template = re.sub(r"CuwC", "CuuC", template)
    template = re.sub(r"CiyC", "CiiC", template)
    template = re.sub(r"CAC", "CaaC", template)

    # Alif madda
    template = re.sub(r"\|", "2aa", template)

    # glotal stops
    template = re.sub(r"[><&}]", "2", template)

    # initial A, or hamzat wasl
    template = re.sub(r"(^A|^{)", 'a', template)

    # glides followed by long vowel aa
    template = re.sub(r"(aw|iy)A", r'\1aa', template)

    # ta marbuta
    template = re.sub(r"ap", "+at", template)

    # ending vowels
    template = re.sub(r"(aY|A$)", 'aa', template)
    template = re.sub(r"(Ciy$)", 'Cii', template)
    template = re.sub(r"(Cuw$)", 'Cuu', template)


    return template
def main():
    db = MorphologyDB("calima-msa-s31_0.4.2.utf8.db", 'g')

    plurals = []
    pl_type = ''

    word_counts, lemma_counts = _trim_corpus(sys.argv[1], 2)

    with open(sys.argv[1], 'r') as f:
        for line in f:
            if not line.startswith('*'):
                continue
            elif 'pos:noun ' not in line:
                continue

            features = _parse_analysis_line_toks(line.strip().split(' ')[1:])
            # if features['diac'] not in word_counts:
            #     continue
            if features['num'] == 's':
                continue

            if (features['num'] == 'p') and (features['form_num'] == 'p'):
                pl_type = 'S'
            elif (features['num'] == 'p') and (features['form_num'] == 's'):
                pl_type = 'B'
            else:
                continue
            plural_bswrd = _REMOVE_FNL_DCRTC.sub('' , _REMOVE_CLTCS.sub('', features['d3tok']))
            patt = features['pattern']

            if _PRC_STR.findall(features['d3seg']) != []: 
                prc_str = _UNDRSCR_PLS.sub('', _PRC_STR.findall(features['d3seg'])[0])
                patt = re.sub(prc_str, '', patt)
            if _ECN_STR.findall(features['d3seg']) != []:
                enc_str = _UNDRSCR_PLS.sub('', _ECN_STR.findall(features['d3seg'])[0])
                patt = re.sub(enc_str, '', patt)

            patt = _REMOVE_FNL_DCRTC.sub('', patt)
            if pl_type == 'S':
                plural_bswrd = _NORM_SOUND.sub('iyn', plural_bswrd)
                patt = _NORM_SOUND.sub('iyn', patt)

            # get the pattern of the lemma (singular form) from the database.
            # make sure that we are looking at the stem of the singular form
            lex_patt = ar2bw(db.lemma_hash[bw2ar(features['lex'])][0]['pattern'])
            for item in db.lemma_hash[bw2ar(features['lex'])]:
                if features['lex'].endswith('ap'):
                    if item['diac'] == bw2ar(features['lex'])[0:-2]:
                        lex_patt = ar2bw(item['pattern'])+'ap'
                        break
                elif item['diac'] == bw2ar(features['lex']):
                    lex_patt = ar2bw(item['pattern'])
                    break
            #lemma -- plural -- B/S -- gender -- rat -- root -- lemma_patt -- plural_patt -- lemma_cv -- plural_cv
            plurals.append([features['lex'], plural_bswrd, pl_type, features['gen'], features['rat'],
             features['root'], lex_patt, patt, _generate_cv_template(lex_patt, pl_type), _generate_cv_template(patt, pl_type, 'p')])
            # if patt == '>u2~at':
            #     print(plurals[-1])
        print(len(plurals))
        # print(plurals[999])
    plurals_df = pd.DataFrame(plurals, columns=['lemma', 'plural', 'B/S', 'gender', 'rat', 'root', 
                                            'lemma_patt', 'plural_patt', 'lemma_cv', 'plural_cv'])
    # print(plurals_df[['lemma','plural']].value_counts())
    print("Unique SG-PL pairs:", len(plurals_df[['lemma','plural']].value_counts()))
    print("Unique SG-PL pairs:", len(plurals_df[['lemma','plural']].value_counts()))
    print("Unique SG-PL patts:", len(plurals_df[['lemma_patt','plural_patt']].value_counts()))
    print("Unique SG-PL CVs:", len(plurals_df[['lemma_cv','plural_cv']].value_counts()))
    print("Unique lines:", len(plurals_df[['lemma', 'plural', 'B/S', 'gender', 'rat', 'root', 
                                            'lemma_patt', 'plural_patt', 'lemma_cv', 'plural_cv']].value_counts()))
    print(plurals_df[['lemma', 'plural', 'B/S', 'gender', 'rat', 'root', 
                                            'lemma_patt', 'plural_patt', 'lemma_cv', 'plural_cv']].value_counts().to_csv("unique_lines.csv"))

    plurals_df[['lemma_cv','plural_cv', 'B/S']].value_counts().to_csv("all_cv_counts.csv")
    plurals_df[['lemma_patt','plural_patt', 'B/S']].value_counts().to_csv("all_patt_counts.csv")
    plurals_df[['plural_cv', 'B/S']].value_counts().to_csv("plural_cv_counts.csv")
    plurals_df[['plural_patt', 'B/S']].value_counts().to_csv("plural_patt_counts.csv")
    plurals_df[['gender', 'rat', 'B/S']].value_counts().to_csv("gender_rat_counts.csv")
    plurals_df[['rat', 'B/S']].value_counts().to_csv("rat_cv_counts.csv")
    plurals_df[['gender', 'B/S']].value_counts().to_csv("gender_counts.csv")
    unique_plurals = plurals_df.drop_duplicates()
    unique_plurals[['lemma_cv','plural_cv', 'B/S']].value_counts().to_csv("cv_type_counts.csv")



    print(plurals_df[['B/S']].value_counts())









if __name__ == "__main__":
    main()