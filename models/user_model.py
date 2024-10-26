from odmantic import Model

class User(Model):
    name: str
    age: int
    email: str

    model_config = {"collection": "users"}