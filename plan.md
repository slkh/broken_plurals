- What do we have:
  - ATB123 corpus (train/dev/test)
  - Analyzer (if needed)
- What we need:
  - trim the corpus (read Jordan's paper or just ask him)
  - extract the ICs from the corpus
  - decide on features and extract them
  - decide on the input and output
  - Evaluation and analysis

- IC extraction
  - look for nouns and adjectives. (noun, adj)
    - noun_num and noun_quant are a closed class
    - adj_comp has a predictable broken plural (but maybe can be used)
  - Use roots to get patterns or just use Cv or C[iua]?
  - What to do with glides? keep them or have them as consonants
  - Same thing with hamzas and ta-marbuta
- Features:
  - gender, rationality, frequency of singular pattern

---

## Current stats of the ATB123
- This is on nouns only. Adjectives aren't that many as plurals and other types of nouns have weird annotations
- For type counts I did the following: 
  - Basewords only (i.e. all the clitics are removed).
  - Case is removed (or last diacritic is removed)
  - iyn and uwn for sound plurals are just normalized to iyn

### TOKENS
Train:\
38,625 plural nouns\
17,190 are sound	44.5%\
21,434 are broken	55.5%

Dev:\
4,775 plural nouns\
2,002 are sound	41.9%\
2,773 are broken	58.1%

Test:\
4,805 plural nouns\
2,083 are sound	43.3%\
2,722 are broken	56.7%

### TYPES
Train:\
2,897 plural nouns\
1,524 are sound	52.6%\
1,373 are broken	47.4%

Dev:\
1,155 plural nouns\
571 are sound	49.4%\
584 are broken	50.6%

Test:\
1,147 plural nouns\
556 are sound	48.5%\
591 are broken	51.5%

### collect the plurals
## Things to look out for
- clitics: to be removed
- last diacritic, whether it is a case ending or not (-Ati, -iyna, ...)
- count `iyn` and `uwn` as the same.
- in cases of `idafa` (construct state) in MP, those should be counted as sound.
- encode gender, and rationality as features.
- there are lemmas thata has more than one plural (+1 broken or broken and sound)

lemma -- plural -- B/S -- gender -- rat -- root -- lemma_patt -- plural_patt -- lemma_cv -- plural_cv