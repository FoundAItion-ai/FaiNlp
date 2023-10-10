"""
Filename    :   ImageCog.py
Copyright   :   FoundAItion Inc.
Description :   Image recognition
Written by  :   Alex Fedosov
Created     :   07/27/2023
Updated     :   07/27/2023
"""

import logging
import os
import clip
import PIL
import sys
import torch


log = logging.getLogger(__name__)


class ImageCog():
    DEFAULT_MODEL = "ViT-B-32.pt"  # ViT-B/32
    PROBABILITY_THRESHOLD = 90  # %

    def __init__(self, model_name=DEFAULT_MODEL) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        model_path = os.path.join("ImageCog\models", model_name)
        if getattr(sys, 'frozen', False):
            self.full_path_to_model = os.path.join(sys._MEIPASS, model_path)
        else:
            self.full_path_to_model = os.path.join(os.path.dirname(__file__), model_path)

        self.model = self.preprocess = None

    def recognize(self, image, labels) -> str:
        """Zero-shot image classification
        returns the most probable label
        """
        if not isinstance(labels, list):
            raise Exception("Invalid argument type, labels is not a list")
        if not labels:
            raise Exception("Empty labels list")
        if not isinstance(image, PIL.Image.Image):
            raise Exception("Invalid argument type, image is not a PIL Image")
        
        try:
            if self.model is None or self.preprocess is None:
                self.model, self.preprocess = clip.load(self.full_path_to_model, device=self.device)
                log.debug(f"Model loaded, {self.device=} / {self.full_path_to_model=}")

            image_input  = self.preprocess(image).unsqueeze(0).to(self.device)
            text_inputs = torch.cat([clip.tokenize(label) for label in labels]).to(self.device)

            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                text_features =  self.model.encode_text(text_inputs)

            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            values, indices = similarity[0].topk(len(labels))
            recognized_label = ""
            result_verbose = ""
            recognized_probability = 0

            for value, index in zip(values, indices):
                label = labels[index]
                probability = 100 * value.item()
                result_verbose = result_verbose + f"{label:s}: {probability:.2f}% \n"
                if probability > ImageCog.PROBABILITY_THRESHOLD:
                    recognized_label = label
                    recognized_probability = probability

            log.debug(f"Image recognition result: {result_verbose=}")
            return recognized_label, recognized_probability, result_verbose
        except Exception as err:
            log.error(f"Image recognition exception: {err}")
            return "", 0, ""