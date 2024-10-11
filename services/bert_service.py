from ai.predict import BERTPredictor

class BERTService:
    def __init__(self):
        self.predictor = BERTPredictor()

    def predict_attack(self, log_data: str):
        preprocessed_logs = self.predictor.preprocess_logs(log_data)
        prediction = self.predictor.predict(preprocessed_logs)
        return {"prediction": prediction}