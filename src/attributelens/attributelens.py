from collections import defaultdict

import src.attributelens.utils as lens_utils
from src.functional import compute_hidden_states
from src.models import ModelAndTokenizer, determine_layer_paths
from src.operators import LinearRelationOperator
from src.utils import tokenizer_utils

import numpy as np
import torch
from baukit import nethook
from transformers import AutoModelForCausalLM, AutoTokenizer


class Attribute_Lens:
    def __init__(
        self,
        mt: ModelAndTokenizer,
        top_k: int = 10,
        layer_output_tmp: str = "h.{}",
    ):
        self.mt = mt
        self.top_k = top_k
        self.layers = determine_layer_paths(mt)
        self.layer_output_tmp = layer_output_tmp

    def apply_attribute_lens(
        self,
        prompt: str,
        relation_operator: LinearRelationOperator
    ) -> dict:
        print("prompt: ", prompt)

        inputs = self.mt.tokenizer(
            prompt, return_tensors="pt"
        ).to(self.mt.model.device)

        subject_start, subject_end = 0, inputs['input_ids'].size(1)
        prompt_tokenized = [self.mt.tokenizer.decode(t) for t in inputs.input_ids[0]]
        v_space_reprs: list = []

        [hss, out] = compute_hidden_states(
            mt=self.mt, layers=list(range(len(self.layers))), inputs=inputs
        )
        nextwords = [self.mt.tokenizer.decode(t) for t in out['logits'].max(-1)[1][0]]

        for sub_idx in range(subject_start, subject_end):
            v_space_reprs.append(defaultdict(list))
            for layer_idx in range(len(self.layers)):
                predictions = relation_operator(
                    subject='', # Not used if h is passed
                    k=self.top_k,
                    h=hss[layer_idx][:, sub_idx],
                ).predictions

                v_space_reprs[sub_idx - subject_start][
                    self.layer_output_tmp.format(layer_idx)
                ] = [(p.token, p.prob) for p in predictions]

        ret_dict = {}
        ret_dict["prompt_tokenized"] = prompt_tokenized
        ret_dict["v_space_reprs"] = v_space_reprs
        ret_dict["subject_range"] = (subject_start, subject_end)
        ret_dict["nextwords"] = nextwords

        return ret_dict
