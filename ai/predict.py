from ai.model_loader import load_model
import torch

class BERTPredictor:
    def __init__(self):
        self.model, self.tokenizer, self.label_encoder = load_model()

    def preprocess_logs(self, data):
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

    def predict(self, logs):
        input_text = " ".join(logs)
        inputs = self.tokenizer(input_text, padding='max_length', truncation=True, return_tensors='pt', max_length=512)
        input_ids = inputs['input_ids'].squeeze()
        attention_mask = inputs['attention_mask'].squeeze()

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids.unsqueeze(0), attention_mask=attention_mask.unsqueeze(0))
            logits = outputs.logits
            predicted_labels = torch.argmax(logits, dim=-1)
            decoded_predictions = self.label_encoder.inverse_transform(predicted_labels.cpu().numpy().flatten())

        most_common_prediction = max(set(decoded_predictions), key=list(decoded_predictions).count)
        return most_common_prediction