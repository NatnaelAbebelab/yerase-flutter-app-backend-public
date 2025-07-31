import uuid

class OrderIDGenerator:
    @staticmethod
    def generate_short_order_id():
        return uuid.uuid4().hex[:6]