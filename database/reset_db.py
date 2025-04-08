from database.db import engine
from database.models import Base

def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped successfully!")
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")

if __name__ == "__main__":
    reset_database()