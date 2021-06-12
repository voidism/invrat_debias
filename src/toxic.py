# coding=utf-8
# This code was copied from
# (https://github.com/huggingface/transformers/)
# and amended by Xuhui Zhou. All modifications are licensed under Apache 2.0 as is the
# original code. See below for the original license:

# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Toxic language data processors and helpers """

import logging
import os
import re
import csv
import copy
import pandas as pd
import json

from transformers import is_tf_available
from transformers import DataProcessor, InputExample, InputFeatures


if is_tf_available():
    import tensorflow as tf

logger = logging.getLogger(__name__)

class EnvInputExample(object):
    """
    A single training/test example for simple sequence classification.

    Args:
        guid: Unique id for the example.
        text_a: string. The untokenized text of the first sequence. For single
        sequence tasks, only this sequence must be specified.
        text_b: (Optional) string. The untokenized text of the second sequence.
        Only must be specified for sequence pair tasks.
        label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """
    def __init__(self, guid, text_a, text_b=None, label=None, env=None):
        self.guid = guid
        self.text_a = text_a
        self.text_b = text_b
        self.label = label
        self.env = env

    def __repr__(self):
        return str(self.to_json_string())

    def to_dict(self):
        """Serializes this instance to a Python dictionary."""
        output = copy.deepcopy(self.__dict__)
        return output

    def to_json_string(self):
        """Serializes this instance to a JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def glue_convert_examples_to_features(examples, tokenizer,
                                      max_length=512,
                                      task=None,
                                      label_list=None,
                                      output_mode=None,
                                      pad_on_left=False,
                                      pad_token=0,
                                      pad_token_segment_id=0,
                                      mask_padding_with_zero=True):
    """
    Loads a data file into a list of ``InputFeatures``

    Args:
        examples: List of ``InputExamples`` or ``tf.data.Dataset`` containing the examples.
        tokenizer: Instance of a tokenizer that will tokenize the examples
        max_length: Maximum example length
        task: GLUE task
        label_list: List of labels. Can be obtained from the processor using the ``processor.get_labels()`` method
        output_mode: String indicating the output mode. Either ``regression`` or ``classification``
        pad_on_left: If set to ``True``, the examples will be padded on the left rather than on the right (default)
        pad_token: Padding token
        pad_token_segment_id: The segment ID for the padding token (It is usually 0, but can vary such as for XLNet where it is 4)
        mask_padding_with_zero: If set to ``True``, the attention mask will be filled by ``1`` for actual values
            and by ``0`` for padded values. If set to ``False``, inverts it (``1`` for padded values, ``0`` for
            actual values)

    Returns:
        If the ``examples`` input is a ``tf.data.Dataset``, will return a ``tf.data.Dataset``
        containing the task-specific features. If the input is a list of ``InputExamples``, will return
        a list of task-specific ``InputFeatures`` which can be fed to the model.

    """
    is_tf_dataset = False
    if is_tf_available() and isinstance(examples, tf.data.Dataset):
        is_tf_dataset = True

    if task is not None:
        processor = glue_processors[task]()
        if label_list is None:
            label_list = processor.get_labels()
            logger.info("Using label list %s for task %s" % (label_list, task))
        if output_mode is None:
            output_mode = glue_output_modes[task]
            logger.info("Using output mode %s for task %s" % (output_mode, task))

    label_map = {label: i for i, label in enumerate(label_list)}

    features = []
    for (ex_index, example) in enumerate(examples):
        if ex_index % 10000 == 0:
            logger.info("Writing example %d" % (ex_index))
        if is_tf_dataset:
            example = processor.get_example_from_tensor_dict(example)
            example = processor.tfds_map(example)


        inputs = tokenizer.encode_plus(
            example.text_a,
            example.text_b,
            add_special_tokens=True,
            max_length=max_length,
        )
        input_ids, token_type_ids = inputs["input_ids"], inputs["token_type_ids"]

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        attention_mask = [1 if mask_padding_with_zero else 0] * len(input_ids)

        # Zero-pad up to the sequence length.
        padding_length = max_length - len(input_ids)
        if pad_on_left:
            input_ids = ([pad_token] * padding_length) + input_ids
            attention_mask = ([0 if mask_padding_with_zero else 1] * padding_length) + attention_mask
            token_type_ids = ([pad_token_segment_id] * padding_length) + ([example.env] * len(token_type_ids))
        else:
            input_ids = input_ids + ([pad_token] * padding_length)
            attention_mask = attention_mask + ([0 if mask_padding_with_zero else 1] * padding_length)
            token_type_ids = ([example.env] * len(token_type_ids)) + ([pad_token_segment_id] * padding_length)

        assert len(input_ids) == max_length, "Error with input length {} vs {}".format(len(input_ids), max_length)
        assert len(attention_mask) == max_length, "Error with input length {} vs {}".format(len(attention_mask), max_length)
        assert len(token_type_ids) == max_length, "Error with input length {} vs {}".format(len(token_type_ids), max_length)

        if output_mode == "classification":
            label = label_map[example.label]
        elif output_mode == "regression":
            label = float(example.label)
        else:
            raise KeyError(output_mode) 

        if ex_index < 5:
            logger.info("*** Example ***")
            logger.info("guid: %s" % (example.guid))
            logger.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            logger.info("attention_mask: %s" % " ".join([str(x) for x in attention_mask]))
            logger.info("token_type_ids: %s" % " ".join([str(x) for x in token_type_ids]))
            logger.info("label: %s (id = %d)" % (example.label, label))

        features.append(
                InputFeatures(input_ids=input_ids,
                              attention_mask=attention_mask,
                              token_type_ids=token_type_ids,
                              label=label))

    if is_tf_available() and is_tf_dataset:
        def gen():
            for ex in features:
                yield ({'input_ids': ex.input_ids,
                         'attention_mask': ex.attention_mask,
                         'token_type_ids': ex.token_type_ids},
                        ex.label)

        return tf.data.Dataset.from_generator(gen,
            ({'input_ids': tf.int32,
              'attention_mask': tf.int32,
              'token_type_ids': tf.int32},
             tf.int64),
            ({'input_ids': tf.TensorShape([None]),
              'attention_mask': tf.TensorShape([None]),
              'token_type_ids': tf.TensorShape([None])},
             tf.TensorShape([])))

    return features

class ToxicNewProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        df = pd.read_csv(input_file)
        return df

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_pAPI.csv')), "train")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, df, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(zip(df.tweet, df.ND_label)):
            guid = "%s-%s" % (set_type, i)
            text_a = line[0]
            label = str(line[1])
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples


class ToxicEnvProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""
    env2id = {"aav":0, "hispanic":1, "white":2, "other":3}
    df_word = pd.read_csv("word_based_bias_list.csv")
    noi_wordlist = df_word[df_word.categorization=='harmless-minority'].word.tolist()
    oi_wordlist = df_word[df_word.categorization=='offensive-minority-reference'].word.tolist()
    oni_wordlist = df_word[df_word.categorization=='offensive-not-minority'].word.tolist()

    idtyRe = re.compile(r"\b"+r"\b|\b".join(noi_wordlist)+"\b",re.IGNORECASE)
    oiRe = re.compile(r"\b"+r"\b|\b".join(oi_wordlist)+"\b",re.IGNORECASE)
    oniRe = re.compile(r"\b"+r"\b|\b".join(oni_wordlist)+"\b",re.IGNORECASE)

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
            str(tensor_dict["env"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        df = pd.read_csv(input_file)
        return df

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir, env_type='dialect'):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_pAPI.csv')), "train", env_type=env_type)

    def get_dev_examples(self, data_dir, env_type='dialect'):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev", env_type=env_type)

    def get_test_examples(self, data_dir, env_type='dialect'):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test", env_type=env_type)

    def get_examples(self, data_dir, env_type='dialect'):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev", env_type=env_type)


    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, df, set_type, env_type='dialect'):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(zip(df.tweet, df.ND_label, df.dialect_argmax)):
            guid = "%s-%s" % (set_type, i)
            text_a = line[0]
            label = str(line[1])
            if env_type == 'dialect':
                env = line[2]
                env = ToxicEnvProcessor.env2id[env]
            elif env_type == 'aae':
                env = line[2]
                env = 1 if env == 'aae' else 0 #ToxicEnvProcessor.env2id[env]
            elif env_type == 'mention':
                if len(ToxicEnvProcessor.idtyRe.findall(line[0]))>0:
                    env = 0
                elif len(ToxicEnvProcessor.oiRe.findall(line[0]))>0:
                    env = 1
                elif len(ToxicEnvProcessor.oniRe.findall(line[0]))>0:
                    env = 2
                else:
                    env = 3
            else:
                raise(ValueError("False Env Type: " + env_type))

            examples.append(EnvInputExample(guid=guid, text_a=text_a, text_b=None, label=label, env=env))
        return examples


class ToxicProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return EnvInputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(csv.reader(f, delimiter=",", quotechar=quotechar))

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_pAPI.csv')), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev")

    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[-2]
            label = line[-1]
            examples.append(EnvInputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples


class ToxicTransProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(csv.reader(f, delimiter=",", quotechar=quotechar))

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples_trans(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_persp.trans_persp.csv')), "train")
    
    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev")
    
    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[-2]
            label = line[-1]
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples

    def _create_examples_trans(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[17]
            text_trans = line[18]
            label = str(int(float(line[3])))
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
            examples.append(InputExample(guid=guid, text_a=text_trans, text_b=None, label=label))
        return examples

class ToxicTransreProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(csv.reader(f, delimiter=",", quotechar=quotechar))

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples_trans(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_persp.trans_persp.csv')), "train")
    
    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev")
    
    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[-2]
            label = line[-1]
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples

    def _create_examples_trans(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[17]
            text_trans = line[18]
            label = str(int(float(line[3])))
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=text_trans, label=label))
        return examples


class ToxicEvalProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(csv.reader(f, delimiter=",", quotechar=quotechar))

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir,'ND_founta_trn_dial_pAPI.csv')), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_dev_dial_pAPI.csv")), "dev")
    
    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_founta_tst_dial_pAPI.csv")), "test")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            text_a = line[9]
            text_a_trans = line[11]
            label = line[10]
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
            examples.append(InputExample(guid=guid, text_a=text_a_trans, text_b=None, label=label))
        return examples

    def _create_examples_s(self, lines, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(lines):
            if i == 0:
                continue
            guid = "%s-%s" % (set_type, i)
            line = line.strip()
            line = line.split('\001')
            text_a = line[3]
            label = line[1]
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples

class ToxicDavisonProcessor(DataProcessor):
    """Processor for the SST-2 data set (GLUE version)."""

    def get_example_from_tensor_dict(self, tensor_dict):
        """See base class."""
        return InputExample(
            tensor_dict["idx"].numpy(),
            tensor_dict["sentence"].numpy().decode("utf-8"),
            None,
            str(tensor_dict["label"].numpy()),
        )

    def read_csv(self, input_file, quotechar='"'):
        """Reads a tab separated value file."""
        df = pd.read_csv(input_file)
        return df

    def read_txt(self, input_file):
        """Reads a tab separated value file."""
        with open(input_file, "r", encoding="utf-8-sig") as f:
            return list(f)

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir,'ND_davidson_trn_dial_new.csv')), "train")

    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_davidson_dev_dial_new.csv")), "dev")
    
    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(os.path.join(data_dir, "ND_davidson_tst_dial_new.csv")), "test")

    def get_examples(self, data_dir):
        """See base class."""
        return self._create_examples(self.read_csv(data_dir,'"'), "dev")

    def get_labels(self):
        """See base class."""
        return ["0", "1"]

    def _create_examples(self, df, set_type):
        """Creates examples for the training and dev sets."""
        examples = []
        for (i, line) in enumerate(zip(df.tweet, df.ND_label)):
            guid = "%s-%s" % (set_type, i)
            text_a = line[0]
            label = str(line[1])
            examples.append(InputExample(guid=guid, text_a=text_a, text_b=None, label=label))
        return examples



glue_tasks_num_labels = {
    "cola": 2,
    "mnli": 3,
    "mrpc": 2,
    "sst-2": 2,
    "sts-b": 1,
    "qqp": 2,
    "qnli": 2,
    "rte": 2,
    "wnli": 2,
}

glue_processors = {
    "toxic":ToxicNewProcessor,
    "toxic-env":ToxicEnvProcessor,
    "toxic-davison":ToxicDavisonProcessor,
    "toxic_trans":ToxicTransProcessor
}

glue_output_modes = {
    "cola": "classification",
    "mnli": "classification",
    "mnli-mm": "classification",
    "mrpc": "classification",
    "sst-2": "classification",
    "toxic": "classification",
    "toxic-env": "classification",
    "toxic_eval": "classification",
    "toxic_trans": "classification",
    "toxic-davison": "classification",
    "sts-b": "regression",
    "qqp": "classification",
    "qnli": "classification",
    "rte": "classification",
    "wnli": "classification",
}
