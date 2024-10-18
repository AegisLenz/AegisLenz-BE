from ai.predict import BERTPredictor

class BERTService:
    def __init__(self):
        self.predictor = BERTPredictor()

    async def predict_attack(self, log_data: str):
        preprocessed_logs = await self.predictor.preprocess_logs(log_data)
        prediction = await self.predictor.predict(preprocessed_logs)
        return prediction