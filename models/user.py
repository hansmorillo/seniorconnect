from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, password, role="user"):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    def get_id(self):
        return str(self.id)

# placeholder code, will connect to MySQL in later stages.