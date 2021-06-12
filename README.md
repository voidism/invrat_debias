# Mitigating Biases in Toxic Language Detection through Invariant Rationalization

This is the source code for our paper "Mitigating Biases in Toxic Language Detection through Invariant Rationalization" at ACL-IJCNLP 2021 WOAH workshop (The Firth Workshop on Online Abuse and Harms).
Our code is based on the code of [Challenges in Automated Debiasing for Toxic Language Detection](https://arxiv.org/pdf/2102.00086.pdf).

To reproduce the experiments, please first follow the instruction of the [original repo](https://github.com/XuhuiZhou/Toxic_Debias) to setup the environment. And download the dataset of [Large Scale Crowdsourcing and Characterization of Twitter Abusive Behavior](https://arxiv.org/abs/1802.00393).

You should have a folder `<toxic_data_dir>` that contains three files: `ND_founta_trn_dial_pAPI.csv, ND_founta_dev_dial_pAPI.csv, ND_founta_tst_dial_pAPI.csv', which have the same format as `data/demo.csv`. 

## Training

- `$seed` is your random seed.
- You should specify your own `<output_dir>`.

### Vanilla
```
bash run_vanilla.sh <toxic_data_dir> $seed <output_dir>
```

### InvRat (lexical)
```
bash run_invrat_mention.sh <toxic_data_dir> $seed <output_dir>
```

### InvRat (dialect)
```
# $seed is your random seed
bash run_invrat_dialect.sh <toxic_data_dir> $seed <output_dir>
```

## Evaluation (compute Acc, F1, FPR)

- We take test set & step 56000 for example. You can change test set into dev set, or compute for other steps.
- Your should specify your own `<output_csv_filename>`.

### Vanilla
```
python to_ND.py <output_dir>/test_eval_results.txt-preds-step-56000.txt <toxic_data_dir>/ND_founta_tst_dial_pAPI.csv roberta <output_csv_filename>
python src/bias_stats.py <output_csv_filename> roberta data/word_based_bias_list.csv
```

### InvRat (lexical or dialect)

- You can choose the results from either `invariant` or `variant` classifier that you want to compute. All results shown in our paper is from `invariant` classifier.

```
python inv_to_ND.py <output_dir>/test_eval_results-step-56000.txt-rationale-step-56000.txt <toxic_data_dir>/ND_founta_tst_dial_pAPI.csv <output_csv_filename>
python src/bias_stats.py <output_csv_filename> [variant/invariant] data/word_based_bias_list.csv
```
