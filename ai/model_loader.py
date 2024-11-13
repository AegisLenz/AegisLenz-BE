import os
import torch
import pickle
from dotenv import load_dotenv
from transformers import BertTokenizer, BertForTokenClassification

load_dotenv()


def load_model():
    model_path = os.getenv("MODEL_PATH")
    label_encoder_path = os.getenv("LABEL_ENCODER_PATH")

    with open(label_encoder_path, 'rb') as f:
        label_encoder = pickle.load(f)

    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
    model = BertForTokenClassification.from_pretrained('bert-base-uncased', num_labels=len(label_encoder.classes_))
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    return model, tokenizer, label_encoder
