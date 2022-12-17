from .base import Model
from .fields import *
from .models import *

if __name__ == '__main__':
    class User(Model):
        id = Integer(pk=True)
        name = String()

    class Profile(Model):
        id = Integer(pk=True)
        user_id = Integer(fk=User.id)

    import logging
    class Logging(Config):
        level = Enum(map=logging)

    print(User.id)
    user = User(id=1, name="a")
    print(user)
    print(Profile.user_id.foreign_key)