from app.domain.entities.subscription import Subscription
from typing import Optional

class SqlAlchemySubscriptionRepository:
    def __init__(self, session):
        self.session = session

    def add(self, subscription: Subscription):
        # Add subscription to DB
        pass

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        # Retrieve subscription by user_id
        pass

    def update(self, subscription: Subscription):
        # Update subscription in DB
        pass

    def delete(self, subscription_id: int):
        # Delete subscription from DB
        pass
