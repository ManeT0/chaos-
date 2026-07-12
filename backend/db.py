from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./chaos.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)
    
    teams = relationship("TeamMembership", back_populates="user")

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    members = relationship("TeamMembership", back_populates="team")
    projects = relationship("Project", back_populates="team")

class TeamMembership(Base):
    __tablename__ = "team_memberships"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    
    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="members")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    slo_target = Column(Float, default=99.9)
    error_budget_minutes = Column(Integer, default=43)
    
    team = relationship("Team", back_populates="projects")
    experiments = relationship("Experiment", back_populates="project")

class SLO(Base):
    __tablename__ = "slos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    prometheus_expr = Column(String)
    target_ratio = Column(Float)
    window_hours = Column(Integer, default=720)

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    status = Column(String)
    target = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship("Project", back_populates="experiments")
    runs = relationship("ExperimentRun", back_populates="experiment")

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    status = Column(String)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(String, nullable=True)
    
    experiment = relationship("Experiment", back_populates="runs")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    resource = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


def init_db(path: str = "chaos.db"):
    global engine
    global SessionLocal
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
