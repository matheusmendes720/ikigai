import sys
import os

# Add src to path
sys.path.append(os.path.abspath('vibe-ops/src'))

try:
    from models import DocBackend, DocFrontend, PriorityMatrix, CyberneticFeedback
    from storage import DocBackendORM, DocFrontendORM, PriorityMatrixORM, CyberneticFeedbackORM, Base
    
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

except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
