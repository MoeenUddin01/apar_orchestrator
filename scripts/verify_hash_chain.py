import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import sqlalchemy
from src.database.connection import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.database.audit_repository import AuditRepository
from src.database.models.audit_models import AuditEventDB

# Strip out query arguments like ?prepared_statement_cache_size=0
base_url = settings.DATABASE_URL.split("?")[0]
url = base_url.replace("postgresql+asyncpg", "postgresql")

def test():
    try:
        engine = create_engine(url)
        session = Session(engine)
        repo = AuditRepository(session)
        
        # Get all distinct workflows
        workflows = session.query(AuditEventDB.workflow_id).distinct().all()
        
        valid = 0
        invalid = 0
        
        for (wf_id,) in workflows:
            events = repo.get_workflow_events(wf_id)
            if len(events) > 1:
                is_valid, err = repo.verify_chain(wf_id)
                if is_valid:
                    valid += 1
                else:
                    invalid += 1
                    print(f"Invalid workflow: {wf_id} - Error: {err}")
                    
        print(f"Total multi-event workflows checked: {valid + invalid}")
        print(f"Valid: {valid}, Invalid: {invalid}")
        
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test()
