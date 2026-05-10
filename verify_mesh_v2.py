import sys
import os

# Add src to path
sys.path.append(os.path.abspath('vibe-ops/src'))

try:
    # Import Pydantic models from their specific modules
    from models.doc_entities import DocBackend, DocFrontend
    from models.feedback_entities import PriorityMatrix, CyberneticFeedback
    from models.study_entities import StudyProject, StudyTopic
    
    # Import ORM models directly from orm.py to avoid storage/__init__.py dependencies
    from storage.orm import DocBackendORM, DocFrontendORM, PriorityMatrixORM, CyberneticFeedbackORM, Base, StudyProjectORM
    
    print("All models imported successfully.")
    
    tables = Base.metadata.tables.keys()
    print(f"Tables in metadata: {list(tables)}")
    
    expected_tables = ['docs_backend', 'docs_frontend', 'priority_matrices', 'cybernetic_feedbacks']
    missing = [t for t in expected_tables if t not in tables]
    
    if not missing:
        print("All expected new tables are present in Base.metadata.")
    else:
        print(f"Missing tables: {missing}")
        sys.exit(1)
        
    # Check StudyProjectORM fields
    from sqlalchemy import inspect
    mapper = inspect(StudyProjectORM)
    columns = [c.key for c in mapper.attrs]
    if 'created' in columns and 'updated' in columns:
        print("StudyProjectORM has 'created' and 'updated' fields.")
    else:
        print(f"StudyProjectORM missing fields. Found: {columns}")
        sys.exit(1)

except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
