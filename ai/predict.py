from ai.model_loader import load_model
from transformers import BertTokenizer, BertForTokenClassification
import torch
from collections import Counter

class BERTPredictor:
    def __init__(self):
        self.model, self.tokenizer, self.label_encoder = load_model()

    async def preprocess_logs(self, data):
        preprocessed_data = []
        for idx in range(len(data) - 1, -1, -1):
            user_identity = data[idx].get('userIdentity', {})
            user_type = user_identity.get('type')
            accessKeyId = user_identity.get('accessKeyId', '')[:3]
            eventSource = data[idx].get('eventSource')
            eventTime = data[idx].get('eventTime')
            eventName = data[idx].get('eventName')
            requestParameter = data[idx].get('requestParameter', '')
            responseElements = data[idx].get('responseElements', '')
            resources = data[idx].get('resources')
            readOnly = data[idx].get('readOnly')
            eventType = data[idx].get('eventType')
            eventCategory = data[idx].get('eventCategory')
            managementEvent = data[idx].get('managementEvent')
            errorCode = data[idx].get('errorCode')

            log_text = (f"Time: {eventTime},usertype:{user_type}, accessKeyId:{accessKeyId}, EventName: {eventName},"
                        f" Resource: {resources}, EventSource:{eventSource} eventType: {eventType}, RequestParameter: {requestParameter},"
                        f" ResponseElements:{responseElements}, ReadOnly?:{readOnly}, ManagementEvent?: {managementEvent},"
                        f" EventCategory: {eventCategory}, ErrorCode: {errorCode}")

            preprocessed_data.append(log_text)

        return preprocessed_data
    
    async def sliding_window(self, logs, window_size=5):
        windowed_logs = []
        for i in range(len(logs) - window_size + 1):
            window_logs = logs[i:i + window_size]
            windowed_logs.append(window_logs)

        return windowed_logs
    
    async def consolidate_predictions(self, predictions, num_logs, window_size):

        log_votes = [Counter() for _ in range(num_logs)]

        for i, window_pred in enumerate(predictions):
            for j, label in enumerate(window_pred):
                log_index = i + j
                if log_index < num_logs:
                    log_votes[log_index][label] += 1
                else:
                    final_labels.append("No Attack")

        final_labels = [votes.most_common(1)[0][0] for votes in log_votes]
        return final_labels

    async def predict(self,windowed_logs):
        self.model.eval()
        predictions = []

        for input_text in windowed_logs:
            inputs = self.tokenizer(
                input_text,
                padding='max_length',
                truncation=True,
                return_tensors='pt',
                max_length=512
            )
            input_ids = inputs['input_ids']
            attention_mask = inputs['attention_mask']
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits[:, 0, :] # [batch_size, sequence_length, num_labels]

                # 토큰 단위로 예측 수행
                predicted_labels = torch.argmax(logits, dim=-1)  # [batch_size, sequence_length]
                decoded_predictions = self.label_encoder.inverse_transform(predicted_labels.cpu().numpy().flatten())
                predictions.append(decoded_predictions)
        
        return predictions