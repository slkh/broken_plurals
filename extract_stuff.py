import re
import sys
import pandas as pd
from math import log
from collections import Counter

from camel_tools.utils.charmap import CharMapper
from camel_tools.morphology.generator import Generator
from camel_tools.morphology.database import MorphologyDB

bw2ar = CharMapper.builtin_mapper('bw2ar')
ar2bw = CharMapper.builtin_mapper('ar2bw')
bw2safebw = CharMapper.builtin_mapper('bw2safebw')

_PRNTHS = re.compile(r"[\(\)]")

_REMOVE_CLTCS = re.compile(r'(\S+\+\_|\_\+\S+)')
_REMOVE_FNL_DCRTC = re.compile(r'([iouaFKN]|AF)$')
_NORM_SOUND = re.compile(r'uwn$')
_PRC_STR = re.compile(r'(\S+\+\_)+')
_ECN_STR = re.compile(r'(\_\+\S+)+')
_UNDRSCR_PLS = re.compile(r'[\+\_]')
_SUKUN = re.compile(r'o')

_SH_VOWELS = re.compile(r'[aiu]')
_CONS_GLD = re.compile(r'[^aiu]')

_CV_AT_END = re.compile(r'At$')
_CV_IY_IYN_END = re.compile(r'(iy$|iyn$)')
_CV_UW_UWN_END = re.compile(r'(uw$|uwn$)')
_CV_DIGIT = re.compile(r'\d')
_CV_AHMZ_END = re.compile(r"A'$")
_CV_AN_END = re.compile(r"An$")
_CV_U_MID = re.compile(r"CuwC")
_CV_I_MID = re.compile(r"CiyC")
_CV_A_MID = re.compile(r"CAC")
_CV_ALIF_MDD = re.compile(r"\|")
_CV_HMZA = re.compile(r"[><&}']")
_CV_ALIF_INIT = re.compile(r"(^A|^{)")
_CV_GLD_ALIF = re.compile(r"(aw|iy)A")
_CV_TAMAR = re.compile(r"ap")
_CV_A_END = re.compile(r"(aY|A$)")
_CV_I_END = re.compile(r"(Ciy$)")
_CV_U_END = re.compile(r"(Cuw$)")
_CV_ALIF_MQ = re.compile(r"(A|Y)")
_CV_RED_SND = re.compile(r".*(\+iin|\+aat)")

def _create_baseline(test_entries):

    # The baseline is adding the sound suffix according to the gender.
    # because this is just for evaluation, no need to actually add things. 
    # Just check if the word has the suffix
    test_set = test_entries[['gender', 'plural_cv']].values.tolist()
    print(len(test_set))
    correct = 0
    incorrect = 0
    for instance in test_set:
        if (instance[0] == 'f' and instance[1] == '+aat') or \
                                            (instance[0] == 'm' and instance[1] == '+iin'):
            correct +=1
        else:
            incorrect +=1
    print("#####")
    print("Baseline")
    print("Correct:", correct)
    print("Incorrect:", incorrect)
    print("#####")

def _compute_TP(rules):
    prdctv = 0
    unprdctv = 0
    with open(rules+"TP", 'w') as k:
        with open(rules, 'r') as f:
            for line in f:
                is_T = False
                elements = line.strip().split(' ')
                scope = _PRNTHS.sub('', elements[-1].strip()).split('/')
                if len(scope) == 1:
                    is_T = True
                else:
                    is_T = TP(float(scope[0]), float(scope[1]))
                
                if is_T:
                    prdctv += 1
                else:
                    unprdctv +=1
                k.write(f"{line.strip()} {is_T}\n")
    return prdctv, unprdctv

def TP(x,y):
    N = x+y
    # print("Scope of the rule", N)
    # print("Tolerance threshold:",  N/log(N))
    # print("Number of exceptions", y)
    return y <  N/log(N)

def _trim_corpus(file_path, cutoff):
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
    lemma_counts = Counter(lemmas)
    if cutoff != 'all':
        top_n_nouns = list(word_counts.keys())[0:int(cutoff)]
        top_n_lemmas = list(lemma_counts.keys())[0:int(cutoff)]
    else:
        top_n_nouns = list(word_counts.keys())
        top_n_lemmas = list(lemma_counts.keys())

    return top_n_nouns, top_n_lemmas

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

    # for when the template is singular, these will have real values
    melodic_patt = ''
    tamar = False
    # handle sound plurals

    if pl_type == 'S' and pl_sg == 'p':
        if patt.endswith('At'):
            template = _CV_AT_END.sub('+aat', template)
        elif patt.endswith('|t'):
            template = _CV_AT_END.sub('2+aat', template)
        elif patt.endswith(('iyn', 'uwn')):
            template = _CV_IY_IYN_END.sub('+iin', template)
            template = _CV_UW_UWN_END.sub('+iin', template)
        elif patt.endswith(('iy', 'uw')):
            template = _CV_IY_IYN_END.sub('+iin', template)
            template = _CV_UW_UWN_END.sub('+iin', template)
        else:
            print("What kind sound plural is this يا روح أمك?")
            print(patt)

    # to reduce sparsity among the sound plurals, the all we need really is an indicator of which 
    # plural it is, therefore, I'll just replace teh entire template with the suffix. this can obvs be parametrized
    if pl_type == 'S' and pl_sg == 'p':
        template = _CV_RED_SND.sub(r"\1", template)
        return template, melodic_patt, tamar

    # handle non-templatic word stems (NTWS)
    if ('NTWS' in patt) and (pl_sg == 's'):
        return template, 'x', 'False'

    # consonants
    template = _CV_DIGIT.sub('C', template)

    # treat long vowel aa and glotal stop ending as a suffix
    template = _CV_AHMZ_END.sub('+aa2', template)

    # treat aan as a suffix
    template = _CV_AN_END.sub("+aan", template)

    # long vowels aa, ii, uu
    template = _CV_U_MID.sub("CuuC", template)
    template = _CV_I_MID.sub("CiiC", template)
    template = _CV_A_MID.sub("CaaC", template)

    # Alif madda
    template = _CV_ALIF_MDD.sub("2aa", template)

    # glotal stops
    template = _CV_HMZA.sub("2", template)

    # initial A, or hamzat wasl
    template = _CV_ALIF_INIT.sub('a', template)

    # glides followed by long vowel aa
    template = _CV_GLD_ALIF.sub(r'\1aa', template)

    # ta marbuta
    template = _CV_TAMAR.sub("+at", template)

    # ending vowels
    template = _CV_A_END.sub('aa', template)
    template = _CV_I_END.sub('Cii', template)
    template = _CV_U_END.sub('Cuu', template)

    # leftover A and Y
    # if any(x in template for x in ['Y', 'A']):
    #     print(template)
    template = _CV_ALIF_MQ.sub('aa', template)
    if pl_sg == 's':
        if template.endswith('+at'):
            tamar = True
            template = template[:-3]
        melodic_patt = _CONS_GLD.sub('', template)
        template = _SH_VOWELS.sub('v', template)

    return template, melodic_patt, tamar

def _prepare_data(uniq_lines):
    uniq_lines['lemma'] = uniq_lines['lemma'].apply(bw2safebw)
    uniq_lines[['lemma','lemma_cv', 'mel_patt', 'tamar', 'gender', 'rat', 'root', 'plural_cv',
                                'B/S']].to_csv(f'{sys.argv[3]}_plural_top_{sys.argv[2]}.csv', index=False)

def main():


    if sys.argv[1] == 'TP':
        prd, unprd = _compute_TP(sys.argv[2])
        print(f"There are total of {prd+unprd} hypothesized rules, {prd} are productive!")
        sys.exit(2)
    db = MorphologyDB("calima-msa-s31_0.4.2.utf8.db", 'g')
    msa_generator = Generator(db)

    plurals = []
    pl_type = ''
    nouns = []
    num = []
    word_counts, lemma_counts = _trim_corpus(sys.argv[1], sys.argv[2])
    # print(type(word_counts))

    with open(sys.argv[1], 'r') as f:
        for line in f:
            if not line.startswith('*'):
                continue
            elif 'pos:noun ' not in line:
                continue
            features = _parse_analysis_line_toks(line.strip().split(' ')[1:])
            if features['lex'] in lemma_counts:
                nouns.append(features['diac'])
                num.append(features['num'])
            # if features['diac'] not in word_counts: #and (features['lex'] not in word_counts):
            #     continue
            if features['lex'] not in lemma_counts: #and (features['lex'] not in word_counts):
                continue
            if features['num'] in ['s', 'd']:
                analyses = msa_generator.generate(bw2ar(features['lex']), {'pos': 'noun','gen': 
                                                features['gen'],'num': 'p', 'cas':'n', 'stt':'i'})
                if len(analyses) == 0:
                    continue
                features = analyses[0]
                for feat in ['diac', 'lex', 'pattern', 'root', 'd3tok', 'd3seg']:
                    features[feat] = ar2bw(features[feat])

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
            lemma_cv, mel_patt, tamar = _generate_cv_template(lex_patt, pl_type)
            plural_cv, _, _ = _generate_cv_template(patt, pl_type, 'p')

            plurals.append([features['lex'], plural_bswrd, pl_type, features['gen'], features['rat'],
                            features['root'], lex_patt, patt, lemma_cv, mel_patt, tamar, plural_cv])
            # if patt == '>u2~at':
            #     print(plurals[-1])
        print(len(plurals))
        # print(plurals[999])
    plurals_df = pd.DataFrame(plurals, columns=['lemma', 'plural', 'B/S', 'gender', 'rat', 'root', 
                        'lemma_patt', 'plural_patt', 'lemma_cv', 'mel_patt', 'tamar', 'plural_cv'])
    # print(plurals_df[['lemma','plural']].value_counts())
    print("Unique SG-PL pairs:", len(plurals_df[['lemma','plural']].value_counts()))
    print("Unique SG-PL pairs:", len(plurals_df[['lemma','plural']].value_counts()))
    print("Unique SG-PL patts:", len(plurals_df[['lemma_patt','plural_patt']].value_counts()))
    print("Unique SG-PL CVs:", len(plurals_df[['lemma_cv','plural_cv']].value_counts()))
    print("Unique lines:", len(plurals_df[['lemma', 'plural', 'B/S', 'gender', 'rat', 'root', 
                                            'lemma_patt', 'plural_patt', 'lemma_cv', 'plural_cv']].value_counts()))

    plurals_df[['lemma_cv','plural_cv', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_all_cv_counts_{sys.argv[2]}.csv")
    plurals_df[['lemma_patt','plural_patt', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_all_patt_counts_{sys.argv[2]}.csv")
    plurals_df[['plural_cv', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_plural_cv_counts_{sys.argv[2]}.csv")
    plurals_df[['plural_patt', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_plural_patt_counts_{sys.argv[2]}.csv")
    plurals_df[['gender', 'rat', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_gender_rat_counts_{sys.argv[2]}.csv")
    plurals_df[['rat', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_rat_cv_counts_{sys.argv[2]}.csv")
    plurals_df[['gender', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_gender_counts_{sys.argv[2]}.csv")
    unique_plurals = plurals_df.drop_duplicates()
    unique_plurals[['lemma_cv','plural_cv', 'B/S']].value_counts().to_csv(f"{sys.argv[3]}_cv_type_counts_{sys.argv[2]}.csv")

    _prepare_data(unique_plurals)

    if sys.argv[3] in ['test', 'dev']:
        _create_baseline(unique_plurals)

    print(plurals_df[['B/S']].value_counts())
    with open(f"{sys.argv[3]}_labels.csv", 'w') as f:
        f.write('\n'.join(unique_plurals['plural_cv'].unique()))
    print(unique_plurals[['B/S']].value_counts())


    print(f"# of noun tokens in the top {sys.argv[2]} is: {len(nouns)} nouns")
    print(f"# of noun types in the top {sys.argv[2]} is: {len(set(nouns))} nouns")
    print(f"top ten nouns {sys.argv[2]} is: {Counter(nouns).most_common(10)}")
    print(Counter(num))

if __name__ == "__main__":
    main()